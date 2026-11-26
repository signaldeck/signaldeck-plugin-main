"""HTTP and MQTT transport implementations for configured value exports."""
import asyncio
import json
import math
from datetime import datetime, date
from zoneinfo import ZoneInfo
import requests
import paho.mqtt.client as mqtt


def encode(data, zone="Europe/Berlin"):
    def default(value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=ZoneInfo(zone))
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        # numpy scalar values occur in existing processors.
        if hasattr(value, "item"):
            return value.item()
        raise TypeError(f"Unsupported JSON value: {type(value).__name__}")
    return json.dumps(data, default=default, allow_nan=False)


class HttpPublisher:
    def __init__(self, config):
        self.config = config
        self.timeout = float(config.get("timeout_seconds", 5))
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("Invalid HTTP timeout")

    def _send(self, payload):
        headers = dict(self.config.get("headers", {}))
        headers["Content-Type"] = "application/json"
        response = requests.post(
            self.config["url"], data=payload, headers=headers,
            timeout=self.timeout, allow_redirects=False,
        )
        if not 200 <= response.status_code < 300:
            raise ValueError(f"HTTP publish returned {response.status_code}")

    async def publish(self, data):
        await asyncio.to_thread(self._send, encode(data, self.config.get("timezone", "Europe/Berlin")))

    async def shutdown(self):
        pass


class MqttPublisher:
    def __init__(self, config):
        self.config = config
        self.timeout = float(config.get("timeout_seconds", 5))
        self.qos = int(config.get("qos", 0))
        if not math.isfinite(self.timeout) or self.timeout <= 0 or self.qos not in (0, 1, 2):
            raise ValueError("Invalid MQTT timeout or QoS")
        self.client = mqtt.Client()
        if config.get("username") is not None:
            self.client.username_pw_set(config["username"], config.get("password"))
        if config.get("tls"):
            self.client.tls_set(ca_certs=config.get("ca_certs"))
        self.client.reconnect_delay_set(1, 120)
        self.client.connect_async(config["host"], int(config.get("port", 8883 if config.get("tls") else 1883)))
        self.client.loop_start()

    def _send(self, payload):
        if not self.client.is_connected():
            raise ConnectionError("MQTT broker not connected")
        info = self.client.publish(self.config["topic"], payload, qos=self.qos, retain=self.config.get("retain", False))
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            raise ConnectionError(f"MQTT publish error {info.rc}")
        info.wait_for_publish(timeout=self.timeout)
        if not info.is_published():
            raise TimeoutError("MQTT publish timed out")

    async def publish(self, data):
        await asyncio.to_thread(self._send, encode(data, self.config.get("timezone", "Europe/Berlin")))

    async def shutdown(self):
        self.client.disconnect()
        await asyncio.to_thread(self.client.loop_stop)
