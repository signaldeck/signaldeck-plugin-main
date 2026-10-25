"""Behavioral coverage for opt-in DummyData daily time series."""
import datetime
import logging
import math
from types import SimpleNamespace

import pandas as pd
import pytest

from signaldeck_sdk import ValueProvider
from signaldeck_plugin_main.processors.dummy_data.data import (
    Data,
    _generate_full_day_series,
)


def make_dummy(hist=None):
    config = {
        "vars": {"float": ["temperature"]},
        "defaults": {"temperature": 20.0},
        "hist": hist or {
            "temperature": {
                "type": "asc", "perDay": 0.5,
                "interval_minutes": 30, "variation": 2.0,
            }
        },
        "export": {
            "values": [{"temperature_export": "temperature"}],
            "methods": [{
                "name": "hist_temperature_export",
                "target_function": "hist", "args": ["temperature"],
            }],
        },
    }
    return Data("dummy", config, SimpleNamespace(), ValueProvider(), False)


def test_daily_history_is_datetime_indexed_series_with_48_points():
    dummy = make_dummy()
    yesterday = datetime.datetime.now().date() - datetime.timedelta(days=1)
    history = dummy.hist("temperature", days=1, fullDay=True)
    assert isinstance(history, pd.Series)
    assert isinstance(history.index, pd.DatetimeIndex)
    assert len(history) == 48
    assert history.index[0] == pd.Timestamp(yesterday)
    assert history.index[-1] == pd.Timestamp(
        datetime.datetime.combine(yesterday, datetime.time(23, 30))
    )
    assert history.index.is_monotonic_increasing
    assert math.isfinite(float(history.mean()))
    assert len(set(history.values)) > 2


def test_legacy_scalar_and_first_last_behavior():
    dummy = make_dummy()
    assert isinstance(dummy.hist("temperature", days=1), float)
    assert isinstance(dummy.hist("temperature", days=1, fullDay=False), float)
    assert isinstance(dummy.hist("temperature", days=1, first=True, fullDay=True), float)
    assert isinstance(dummy.hist("temperature", days=1, last=True, fullDay=True), float)


def test_current_day_does_not_create_future_measurements():
    dummy = make_dummy()
    samples = dummy.hist("temperature", days=0, fullDay=True)
    assert isinstance(samples, pd.Series)
    assert len(samples) <= 48
    assert len(samples) >= 1
    assert samples.index.max() <= pd.Timestamp(datetime.datetime.now())


def test_full_day_is_repeatable_for_fixed_reference():
    now = datetime.datetime(2026, 10, 25, 10, 30)
    day = datetime.datetime(2026, 10, 23, 12, 0)
    cfg = {"type": "asc", "perDay": 0.35, "interval_minutes": 30, "variation": 2.0}
    first = _generate_full_day_series("temperature", 19.0, cfg, target_date=day, now=now)
    second = _generate_full_day_series("temperature", 19.0, cfg, target_date=day, now=now)
    pd.testing.assert_series_equal(first, second)
    assert first.iloc[6] < first.iloc[30]  # 03:00 vs 15:00


@pytest.mark.parametrize("interval", [0, -5, 17, 1441, 2.5, True])
def test_reject_invalid_sample_intervals(interval):
    with pytest.raises(ValueError, match="interval_minutes"):
        _generate_full_day_series(
            "temperature", 20.0,
            {"type": "asc", "interval_minutes": interval},
            target_date=datetime.datetime(2026, 10, 23),
            now=datetime.datetime(2026, 10, 25),
        )


def test_unconfigured_history_keeps_existing_behavior():
    dummy = make_dummy({"temperature": {"type": "asc", "perDay": 0.35}})
    result = dummy.hist("temperature", days=1, fullDay=True)
    assert isinstance(result, float)


def test_per_instance_history_ui_variables_do_not_accumulate():
    x = make_dummy()
    y = make_dummy()
    assert x.hist_per_day_fields == ["temperature_change_per_day"]
    assert y.hist_per_day_fields == ["temperature_change_per_day"]
