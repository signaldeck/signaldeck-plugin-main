import unittest
from datetime import datetime
from types import SimpleNamespace

from signaldeck_plugin_main.processors.script.script_processor import ScriptProcessor
from signaldeck_sdk import CmdResult, ScriptDefinition, ScriptVariable


class FakeCmd:
    def __init__(self):
        self.script = ScriptDefinition(
            name="monitor",
            commands=["sleep 100"],
            variables=[
                ScriptVariable(name="threshold", default="80"),
                ScriptVariable(name="password", type="secret"),
            ],
        )
        first_result = CmdResult(variables={"threshold": "80", "password": "secret"})
        second_result = CmdResult(variables={"threshold": "90", "password": "other"})
        second_result.finish()
        self.runs = [
            SimpleNamespace(run_id="first-id", script_name="monitor", result=first_result,
                            started_at=datetime.now(), status="running"),
            SimpleNamespace(run_id="second-id", script_name="monitor", result=second_result,
                            started_at=datetime.now(), status="completed"),
        ]
        self.current = {"monitor": first_result}
        self.starts = []
        self.stops = []

    def getScript(self, name):
        return self.script if name == self.script.name else None

    def listScripts(self):
        return [self.script]

    def listAliases(self):
        return []

    def getScriptRuns(self, name):
        return list(self.runs) if name == self.script.name else []

    def getScriptRun(self, run_id):
        return next((run for run in self.runs if run.run_id == run_id), None)

    def runScript(self, name, **kwargs):
        self.starts.append((name, kwargs))

    def stopRun(self, run_id):
        self.stops.append(run_id)


class ScriptProcessorConcurrentRunTests(unittest.TestCase):
    def setUp(self):
        self.cmd = FakeCmd()
        self.processor = ScriptProcessor.__new__(ScriptProcessor)
        self.processor.cmd = self.cmd
        self.processor.ctx = SimpleNamespace(t=lambda key, **kwargs: key)

    def test_each_run_has_separate_stop_button_and_masked_secret(self):
        display = self.processor.getDisplayData("monitor", "hash", selected_script="monitor")
        self.assertEqual([run.run_id for run in display.runs], ["first-id", "second-id"])
        buttons = display.buttons()
        self.assertIn("start", buttons)  # A new run is always possible.
        self.assertIn("stop_run_first-id", buttons)
        self.assertNotIn("stop_run_second-id", buttons)
        self.assertEqual(buttons["stop_run_first-id"]["params"]["run_id"], "first-id")
        self.assertEqual(display.getRunVariables(display.runs[0]), [
            {"name": "threshold", "value": "80"},
            {"name": "password", "value": "••••"},
        ])

    def test_stop_targets_one_run_and_rejects_unknown_or_foreign_ids(self):
        self.processor.performActions("monitor", "hash", selected_script="monitor",
                                      stop_run=True, run_id="first-id")
        self.assertEqual(self.cmd.stops, ["first-id"])
        with self.assertRaisesRegex(ValueError, "Unknown run"):
            self.processor.performActions("monitor", "hash", selected_script="monitor",
                                          stop_run=True, run_id="invalid")
        with self.assertRaisesRegex(ValueError, "Unknown run"):
            self.processor.performActions("monitor", "hash", selected_script="other",
                                          stop_run=True, run_id="first-id")

    def test_start_is_allowed_while_another_run_is_active(self):
        self.processor.performActions("monitor", "hash", selected_script="monitor",
                                      start=True, threshold="95")
        self.assertEqual(self.cmd.starts, [
            ("monitor", {"threshold": "95"}),
        ])

    def test_old_sdk_is_rejected_at_registration(self):
        with self.assertRaisesRegex(RuntimeError, "concurrent script runs"):
            self.processor.registerCommands(SimpleNamespace())


if __name__ == "__main__":
    unittest.main()
