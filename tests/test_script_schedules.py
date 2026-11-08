import unittest
from importlib.resources import files
from types import SimpleNamespace
from unittest.mock import Mock

from signaldeck_plugin_main.processors.script.script_display_data import ScriptDisplayData
from signaldeck_plugin_main.processors.script.script_processor import ScriptProcessor


class ScheduleUiTests(unittest.TestCase):
    def test_schedule_buttons_and_placeholders(self):
        ctx = SimpleNamespace(t=lambda key, **kwargs: key)
        data = (ScriptDisplayData(ctx, "abc123")
                .withSelection("hello", "schedule")
                .withScript(SimpleNamespace(variables=[], commands=[]))
                .withSchedules([{"id": "0123456789abcdef0123456789abcdef",
                                 "cron": "0 7 * * *", "enabled": True,
                                 "variables": {}, "overlap_policy": "skip"}]))
        buttons = data.buttons_to_display()
        self.assertIn("tab_schedule", buttons)
        self.assertIn("schedule_new", buttons)
        self.assertIn("schedule_save_0123456789abcdef0123456789abcdef", buttons)
        self.assertIn("schedule_delete_0123456789abcdef0123456789abcdef", buttons)
        self.assertEqual(buttons["schedule_new"]["params"]["schedule_cron"],
                         "@script_schedule_cron_new_abc123")

    def test_pending_run_has_stop_button_in_template(self):
        template = (
            files("signaldeck_plugin_main")
            .joinpath("templates/main/script.html")
            .read_text(encoding="utf-8")
        )
        self.assertIn(
            '{% if run.status in ["pending", "running"] %}', template
        )
        self.assertIn('renderButton("stop_run_" ~ run.run_id, displayData)', template)

    def test_script_processor_delegates_schedule_save(self):
        processor = ScriptProcessor.__new__(ScriptProcessor)
        processor.cmd = Mock()
        processor.cmd.getScript.return_value = SimpleNamespace()
        processor.performActions("*", "abc123", selected_script="hello",
                                 save_schedule=True, schedule_cron="0 7 * * *",
                                 schedule_enabled=False,
                                 schedule_variables_json='{"limit": 3}',
                                 schedule_overlap="allow")
        processor.cmd.saveScriptSchedule.assert_called_once_with(
            "hello", "0 7 * * *", schedule_id=None,
            enabled=False, variables={"limit": 3}, overlap_policy="allow")

    def test_script_processor_delegates_schedule_delete(self):
        processor = ScriptProcessor.__new__(ScriptProcessor)
        processor.cmd = Mock()
        processor.performActions("*", "abc123", selected_script="hello",
                                 delete_schedule=True, schedule_id="schedule-id")
        processor.cmd.deleteScriptSchedule.assert_called_once_with("hello", "schedule-id")


if __name__ == "__main__":
    unittest.main()
