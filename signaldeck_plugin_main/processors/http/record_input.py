from datetime import datetime, timezone
from threading import RLock
from zoneinfo import ZoneInfo
from jsonpath_ng import parse
from signaldeck_sdk import PersistData, Processor


class RecordInput(PersistData, Processor):
    """Shared configured record ingestion, independent of HTTP transport."""

    def __init__(self, name, config, ctx, valueProvider, collect_data):
        super().__init__(name, config, ctx, valueProvider, collect_data)
        self._record_lock = RLock()
        self._mapping = []
        names = set()
        for field in config["mapping"]:
            key = field["name"]
            if key in names:
                raise ValueError(f"Duplicate mapping field: {key}")
            names.add(key)
            path = field["jsonPath"]
            self._mapping.append((field, None if path == "now" else parse(path)))
        if not any(f["name"] == "date" and f.get("type") == "date" for f, _ in self._mapping):
            raise ValueError("Mapping must define a date field of type date")
        for store in config.get("persist", []):
            if store.get("date_field", "date") != "date":
                raise ValueError("HTTP input uses date as the record timestamp")
        self.currVal = None

    def init_current_vals(self, config=None):
        config = self.config if config is None else config
        if not config.get("persist"):
            return None
        return super().init_current_vals(config)

    def getValue(self, fieldName):
        with self._record_lock:
            return (self.currVal or {}).get(fieldName)

    def getCurFieldValue(self, fieldName, **kwargs):
        return self.getValue(fieldName)

    def makeDataAvailable(self, config=None):
        # getValue reads the record directly; never overwrite processor attributes
        # with names from an incoming payload.
        pass

    def _convert(self, value, field):
        kind = field.get("type")
        if value is None:
            raise ValueError(f"Null value for {field['name']}")
        if kind == "date":
            zone = ZoneInfo(field.get("timezone", self.config.get("timezone", "Europe/Berlin")))
            fmt = field.get("date_format")
            if fmt == "ts":
                result = datetime.fromtimestamp(float(value), tz=timezone.utc)
            elif isinstance(value, datetime):
                result = value
            elif fmt:
                result = datetime.strptime(value, fmt)
            else:
                result = datetime.fromisoformat(value)
            return result.replace(tzinfo=zone) if result.tzinfo is None else result
        if kind == "float":
            import math
            result = float(value)
            if not math.isfinite(result):
                raise ValueError("Non-finite number")
            return result
        if kind == "int":
            return int(value)
        if kind in ("str", "string"):
            return str(value)
        if kind == "bool":
            if isinstance(value, bool):
                return value
            if str(value).lower() in ("true", "1"):
                return True
            if str(value).lower() in ("false", "0"):
                return False
            raise ValueError("Invalid boolean")
        return value

    def map_payload(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        record = {}
        for field, expression in self._mapping:
            if expression is None:
                if field.get("type") != "date":
                    raise ValueError("now is only valid for dates")
                zone = ZoneInfo(field.get("timezone", self.config.get("timezone", "Europe/Berlin")))
                value = self.ctx.date.now(zone)
            else:
                matches = expression.find(payload)
                if not matches and not field.get("required", True):
                    continue
                if len(matches) != 1:
                    raise ValueError(f"Expected one value for {field['name']}")
                value = matches[0].value
            try:
                record[field["name"]] = self._convert(value, field)
            except (ValueError, TypeError, OverflowError):
                if field.get("required", True) or not field.get("ignore_invalid", False):
                    raise
        return record

    def enrich_record(self, record):
        """Add derived fields before validation and persistence."""
        return record

    def validate_record(self, record):
        stamp = record.get("date")
        if not isinstance(stamp, datetime) or stamp.utcoffset() is None:
            raise ValueError("Record must contain a timezone-aware date")
        return True

    def on_record_saved(self, record):
        """Hook for accepted records (including those only kept in memory)."""
        pass

    def ingest(self, payload):
        record = self.enrich_record(self.map_payload(payload))
        if not self.validate_record(record):
            return False
        with self._record_lock:
            if self.config.get("ignore_old_records", True) and self.currVal:
                previous = self.currVal.get("date")
                if previous is not None:
                    if previous.tzinfo is None:
                        previous = previous.replace(tzinfo=ZoneInfo(self.config.get("timezone", "Europe/Berlin")))
                    if record["date"].astimezone(timezone.utc) <= previous.astimezone(timezone.utc):
                        return False
            self.save_data(record)
            self.on_record_saved(record)
        return True
