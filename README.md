# SignalDeck Main Plugins

This repository contains the main plugins for the SignalDeck framework.

The ScriptProcessor shows independent in-memory runs of each named script,
including their start time, status, launch variables and recent output. Each
active run has its own Stop button; starting another instance does not replace
an existing one. Finished runs are retained only in a bounded runtime history
and are not restarted when SignalDeck restarts. Requires the matching
concurrent-run version of `signaldeck-sdk`.



## Installation

```bash
pip install signaldeck-plugin-main


Entwicklung:
 ```
 py -m pip install -e . --config-settings editable_mode=compat
 ```

## DummyData: synthetic full-day history

The `signaldeck_plugin_main.processors.dummy_data.data.Data` processor
can simulate measurements throughout a day. The feature is opt-in; existing
configurations continue returning scalar values from `hist()`.

Example `config.hist`:

```json
{
  "hist": {
    "temp_garten": {
      "type": "asc",
      "perDay": 0.35,
      "interval_minutes": 30,
      "variation": 2.0
    }
  }
}
```

When `hist("temp_garten", days=1, fullDay=True)` is called, the
processor returns a Pandas Series with a `DatetimeIndex` and 48
measurements for yesterday, at intervals of 30 minutes. For the current
day (`days=0`), only samples up to the current time are returned.

- `interval_minutes`: integer from 1 to 1440 that evenly divides 1440.
  Required for opting into full-day series.
- `variation`: optional nonnegative amplitude of a reproducible daily
  sine curve, in the same unit as the simulated value. Minimum at 03:00,
  maximum at 15:00 (relative to local wall time). Defaults to zero.
- `type` and `perDay`: retain the existing history trend semantics.

The original single-value result is retained for `fullDay=False`, for
`first=True`/`last=True`, and if no `interval_minutes` is configured.
Daily samples are deterministic for the same reference time and value.
These data are *synthetic*, not sensor measurements.
