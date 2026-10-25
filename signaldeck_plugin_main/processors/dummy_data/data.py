import datetime
import math

import pandas as pd
from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData, Placeholder
from signaldeck_sdk.persistence.persist_data import PersistData
from .dummy_display_data import DummyDisplayData


def days_between(start: datetime.datetime, end: datetime.datetime) -> float:
    """
    Gibt die Anzahl der Tage zwischen zwei datetime-Objekten als Float zurück.
    Positive Zahl, wenn end nach start liegt.
    """
    delta = end - start
    return delta.total_seconds() / 86400.0


def getDateFromString(dateStr, dateFormat):
    if dateStr.lower() == "$now$":
        return datetime.datetime.now()
    try:
        return datetime.datetime.strptime(dateStr, dateFormat)
    except Exception as e:
        raise ValueError(f"Date string '{dateStr}' does not match format '{dateFormat}'") from e


def calc_hist(cur_val, type, perDay=1, days=1):
    if type == "asc":
        res = cur_val - perDay * days
    else:
        res = cur_val + perDay * days
    return res


def _daily_variation(timestamp: datetime.datetime) -> float:
    """Daily sine curve: minimum at 03:00, maximum at 15:00 (local wall time)."""
    minutes = (
        timestamp.hour * 60 + timestamp.minute
        + timestamp.second / 60 + timestamp.microsecond / 60_000_000
    )
    return math.sin(2 * math.pi * (minutes / 1440 - 9 / 24))


def _generate_full_day_series(
    field_name: str,
    current_value,
    hist_config: dict,
    *,
    target_date: datetime.datetime,
    now: datetime.datetime,
) -> pd.Series:
    """Return a reproducible synthetic time series with a DatetimeIndex.

    The existing scalar history remains the default. This helper is used
    only when fullDay=True and interval_minutes has been configured.

    Values follow the configured per-day trend and optionally add a sine
    curve with amplitude `variation`. The oscillation is relative to the
    current time, so at the reference instant the series agrees with the
    configured current value.

    Timezone-naive datetimes deliberately represent the same local wall
    times as the existing DummyData processor; no timezone is invented.
    """
    interval = hist_config.get("interval_minutes")
    if (
        type(interval) is not int or interval < 1 or interval > 1440
        or 1440 % interval
    ):
        raise ValueError(
            f"hist.{field_name}.interval_minutes must be a positive integer "
            "dividing 1440 (minutes per day)"
        )

    if isinstance(current_value, bool) or not isinstance(current_value, (int, float)):
        raise ValueError(f"hist.{field_name}: synthetic series requires a numeric value")
    if not math.isfinite(float(current_value)):
        raise ValueError(f"hist.{field_name}: value must be finite")

    try:
        per_day = float(hist_config.get("perDay", 1))
        amplitude = float(hist_config.get("variation", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"hist.{field_name}: perDay and variation must be numeric") from exc
    if not math.isfinite(per_day):
        raise ValueError(f"hist.{field_name}.perDay must be finite")
    if not math.isfinite(amplitude) or amplitude < 0:
        raise ValueError(f"hist.{field_name}.variation must be finite and nonnegative")

    kind = hist_config.get("type")
    if kind not in {"asc", "desc"}:
        raise ValueError(f"hist.{field_name}: history type must be asc or desc")

    day_start = datetime.datetime.combine(target_date.date(), datetime.time.min)
    index = pd.date_range(
        start=day_start,
        periods=1440 // interval,
        freq=pd.Timedelta(minutes=interval),
    )
    # A history should never advertise measurements in the future.
    # Previous dates yield the complete configured sampling grid, while
    # the current day contains samples only up to the current minute.
    index = index[index <= pd.Timestamp(now)]
    variation_now = amplitude * _daily_variation(now)
    values = [
        calc_hist(
            float(current_value), kind,
            perDay=per_day,
            days=days_between(timestamp.to_pydatetime(), now),
        )
        + amplitude * _daily_variation(timestamp.to_pydatetime())
        - variation_now
        for timestamp in index
    ]
    return pd.Series(values, index=index, name=field_name, dtype="float64")


class Data(PersistData, DisplayProcessor):

    def __init__(self, name, config, ctx, valueProvider, collect_data):
        super().__init__(name, config, ctx, valueProvider, collect_data)
        self.hist_config = dict(self.config.get("hist", {}))
        # This is per-instance state, not shared across DummyData processors.
        self.hist_per_day_fields = []
        for n, v in self.getValues().items():
            setattr(self, n, v)
        for field, val in self.hist_config.items():
            if "perDay" in val.keys():
                self.hist_per_day_fields.append(f'{field}_change_per_day')

    @classmethod
    def config_placeholders(cls):
        return [Placeholder("DATE_FORMAT", "Date format?", "str", default="%d.%m.%Y %H:%M:%S")]

    def getTemplate(self, value):
        return "main/dummy_data.html"

    def getDisplayData(self, value, actionHash, **kwargs) -> DisplayData:
        return DummyDisplayData(self.ctx, actionHash).withData(self.getValues()).withHistConfig(self.hist_config)

    def performActions(self, value, actionHash, **kwargs):
        for k, v in kwargs.items():
            if k.endswith("change_per_day"):
                self.hist_config[k.split("_change_per")[0]]["perDay"] = v
            else:
                setattr(self, k, v)
        print(kwargs)
        print(self.hist_config)

    def getValues(self):
        res = {}
        for n in self.getBoolParams() + self.getIntParams() + self.getFloatParams():
            if not n.endswith("change_per_day"):
                res[n] = getattr(self, n, self.config.get("defaults", {}).get(n, None))
        for n in self.getDateParams():
            tres = getattr(self, n, self.config.get("defaults", {}).get(n, None))
            if isinstance(tres, str):
                tres = getDateFromString(tres, self.config.get("date_format", "%d.%m.%Y %H:%M:%S"))
            res[n] = tres
        return res

    def getValNames(self):
        return self.getBoolParams() + self.getIntParams() + self.getFloatParams() + self.getDateParams()

    def getDateParams(self):
        return self.config.get("vars", {}).get("date", [])

    def getBoolParams(self):
        return self.config.get("vars", {}).get("bool", [])

    def getIntParams(self):
        return self.config.get("vars", {}).get("int", [])

    def getFloatParams(self):
        return self.config.get("vars", {}).get("float", []) + self.hist_per_day_fields

    def hist(self, fieldName, config=None, days=1, date=None, first=False, last=False, dropna=True, fullDay=False, recursive=True, current=False, currentValues=False, **kwargs):
        res = self.getValue(fieldName)
        hist_config = self.hist_config.get(fieldName, None)
        self.logger.info(
            "Calculating history for field %s with config %s and params "
            "days=%s, date=%s, first=%s, last=%s, dropna=%s, fullDay=%s, "
            "recursive=%s, current=%s, currentValues=%s",
            fieldName, hist_config, days, date, first, last, dropna, fullDay,
            recursive, current, currentValues,
        )
        if hist_config is None:
            return res
        now = datetime.datetime.now()
        if date is None:
            date = now + datetime.timedelta(days=-days)

        # Opt-in synthetic time series. Scalar, first/last and default
        # behavior remain backwards-compatible when fullDay is False.
        if fullDay and "interval_minutes" in hist_config and not (first or last):
            # Round to a minute, making repeated requests within that minute
            # deterministic, and avoiding false sub-minute precision.
            reference_time = now.replace(second=0, microsecond=0)
            series = _generate_full_day_series(
                fieldName, res, hist_config,
                target_date=date, now=reference_time,
            )
            self.logger.info(
                "Generated %d synthetic history samples for %s on %s",
                len(series), fieldName, date.date(),
            )
            return series

        if last:
            if days > 0:
                date = date.replace(hour=23, minute=59, second=59)
        if first:
            date = date.replace(hour=0, minute=0, second=0)
        floatDays = -days_between(now, date)

        if hist_config.get("type") == "asc" or hist_config.get("type") == "desc":
            res = calc_hist(
                res, hist_config.get("type"),
                hist_config.get("perDay", 1), days=floatDays,
            )
        self.logger.info("Calculated history value for field %s: %s", fieldName, res)
        return res
