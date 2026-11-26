import asyncio
import math
import requests
from .record_input import RecordInput


class HttpPoller(RecordInput):
    def __init__(self, name, config, ctx, valueProvider, collect_data):
        super().__init__(name, config, ctx, valueProvider, collect_data)
        self.interval = float(config["interval_seconds"])
        self.timeout = float(config.get("timeout_seconds", 5))
        if not all(math.isfinite(x) and x > 0 for x in (self.interval, self.timeout)):
            raise ValueError("HTTP interval and timeout must be positive and finite")

    def get_asyncio_tasks(self, collect_data):
        return [self._poll_loop()] if collect_data else []

    def _fetch(self):
        response = requests.get(
            self.config["url"], headers=self.config.get("headers"),
            timeout=self.timeout, allow_redirects=False,
        )
        if not 200 <= response.status_code < 300:
            raise ValueError(f"HTTP poll returned {response.status_code}")
        return response.json()

    async def poll_once(self):
        payload = await asyncio.to_thread(self._fetch)
        return self.ingest(payload)

    async def _poll_loop(self):
        while True:
            try:
                await self.poll_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger.exception("HTTP polling failed for %s", self.name)
            await asyncio.sleep(self.interval)
