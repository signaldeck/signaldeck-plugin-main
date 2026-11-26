import asyncio
import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch
from signaldeck_sdk import ValueProvider
from signaldeck_sdk.context import DateProvider
from signaldeck_sdk.value_provider import HttpRequestError
from signaldeck_plugin_main.processors.http.http_receiver import HttpReceiver
from signaldeck_plugin_main.processors.http.http_poller import HttpPoller
from signaldeck_plugin_main.publishers import encode, HttpPublisher, MqttPublisher


def config():
    return {
        "mapping": [
            {"name": "date", "type": "date", "jsonPath": "$.date"},
            {"name": "power", "type": "float", "jsonPath": "$.power"},
        ],
        "cacheSize": 10,
        "export": {"values": [{"remote_power": "power"}], "http": [{"name": "energy", "values": {}}]},
        "url": "http://example.test/energy", "interval_seconds": 30,
    }


PAYLOAD = {"date": "2026-01-01T10:00:00+00:00", "power": "42.5"}


class ReceiverTests(unittest.TestCase):
    def test_records_and_duplicate(self):
        vp = ValueProvider()
        receiver = HttpReceiver("remote", config(), SimpleNamespace(date=DateProvider()), vp, True)
        self.assertIsNone(vp.getValue("remote_power"))
        self.assertTrue(vp.dispatchHttp("energy", "POST", PAYLOAD)["accepted"])
        self.assertEqual(vp.getValue("remote_power"), 42.5)
        self.assertEqual(receiver.getValue("date"), datetime(2026, 1, 1, 10, tzinfo=timezone.utc))
        self.assertFalse(receiver.processHTTPCall(**PAYLOAD)["accepted"])
        self.assertEqual(len(receiver.memory["remote"]), 1)
        with self.assertRaises(HttpRequestError):
            receiver.processHTTPCall(power=10)

    def test_optional_persistence(self):
        cfg = config()
        cfg["persist"] = [{"type": "db", "date_field": "date", "fields": [
            {"name": "date", "dtype": "date"}, {"name": "power", "dtype": "float"}
        ]}]
        receiver = HttpReceiver("remote", cfg, SimpleNamespace(date=DateProvider()), ValueProvider(), True)
        store = Mock()
        store.should_save.return_value = True
        store.use_previous_value.return_value = False
        receiver.registerDataStores({"db": store})
        receiver.processHTTPCall(**PAYLOAD)
        self.assertEqual(store.save.call_args.args[1]["power"], 42.5)


class AsyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_poller(self):
        poller = HttpPoller("remote", config(), SimpleNamespace(date=DateProvider()), ValueProvider(), True)
        with patch.object(poller, "_fetch", return_value=PAYLOAD):
            self.assertTrue(await poller.poll_once())
        self.assertEqual(poller.getValue("power"), 42.5)
        self.assertEqual(poller.get_asyncio_tasks(False), [])

    async def test_http_publish(self):
        publisher = HttpPublisher({"url": "http://example.test"})
        with patch("signaldeck_plugin_main.publishers.requests.post") as post:
            post.return_value.status_code = 200
            await publisher.publish({"date": datetime(2026, 1, 1, tzinfo=timezone.utc)})
            self.assertEqual(json.loads(post.call_args.kwargs["data"])["date"], "2026-01-01T00:00:00+00:00")

    async def test_mqtt_publish(self):
        with patch("signaldeck_plugin_main.publishers.mqtt.Client") as factory:
            client = factory.return_value
            client.is_connected.return_value = True
            client.publish.return_value.rc = 0
            client.publish.return_value.is_published.return_value = True
            publisher = MqttPublisher({"host": "localhost", "topic": "energy", "qos": 1})
            await publisher.publish({"power": 42})
            self.assertEqual(json.loads(client.publish.call_args.args[1]), {"power": 42})
            await publisher.shutdown()
            client.disconnect.assert_called_once()
