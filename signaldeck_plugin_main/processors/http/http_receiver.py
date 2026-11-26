from signaldeck_sdk.value_provider import HttpRequestError
from .record_input import RecordInput


class HttpReceiver(RecordInput):
    def __init__(self, name, config, ctx, valueProvider, collect_data):
        # New endpoints are explicit POST receivers by default.
        for endpoint in config.get("export", {}).get("http", []):
            endpoint["receive"] = True
        super().__init__(name, config, ctx, valueProvider, collect_data)

    def processHTTPCall(self, **payload):
        if not self.collect_data:
            raise HttpRequestError("Data collection is disabled", 503)
        try:
            stored = self.ingest(payload)
        except (ValueError, TypeError, OverflowError) as exc:
            raise HttpRequestError(str(exc)) from exc
        return {"status": "OK", "accepted": stored}
