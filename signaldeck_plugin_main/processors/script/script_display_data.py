import json

from signaldeck_sdk import DisplayData


NEW_SCRIPT = "__new__"


class ScriptDisplayData(DisplayData):
    def __init__(self, ctx, action_hash):
        super().__init__(ctx, action_hash)
        self.scripts = []
        self.aliases = []
        self.selected_script = None
        self.tab = "run"
        self.script = None
        self.cmd_res = None
        self.runs = []
        self.schedules = []
        self.variable_values = {}
        self.new_script_name = ""

    def withScripts(self, scripts):
        self.scripts = scripts
        return self

    def withAliases(self, aliases):
        self.aliases = aliases
        return self

    def withSelection(self, selected_script, tab):
        self.selected_script = selected_script
        self.tab = tab
        return self

    def withScript(self, script):
        self.script = script
        return self

    def withCmdResult(self, cmd_res):
        self.cmd_res = cmd_res
        return self

    def withSchedules(self, schedules):
        self.schedules = list(schedules)
        return self

    def scheduleCronId(self, key):
        return f"script_schedule_cron_{key}_{self.hash}"

    def scheduleVariablesId(self, key):
        return f"script_schedule_vars_{key}_{self.hash}"

    def scheduleEnabledId(self, key):
        return f"script_schedule_enabled_{key}_{self.hash}"

    def scheduleOverlapId(self, key):
        return f"script_schedule_overlap_{key}_{self.hash}"

    def withRuns(self, runs):
        self.runs = list(runs)
        return self

    def withVariableValues(self, values):
        self.variable_values = values
        return self

    def withNewScriptName(self, name):
        self.new_script_name = name or ""
        return self

    def isNewScript(self):
        return self.selected_script == NEW_SCRIPT

    def hasScript(self):
        return self.script is not None and not self.isNewScript()

    def getSelectId(self):
        return f"script-select-{self.hash}"

    def getVariableInputId(self, name):
        return f"script_var_{name}_{self.hash}"

    def getCommandsInputId(self):
        return f"script_commands_{self.hash}"

    def getVariablesInputId(self):
        return f"script_variables_json_{self.hash}"

    def getScriptNameInputId(self):
        return f"script_name_{self.hash}"

    def getAliasValueInputId(self, index):
        return f"script_alias_value_{index}_{self.hash}"

    def getNewAliasNameInputId(self):
        return f"script_alias_new_name_{self.hash}"

    def getNewAliasValueInputId(self):
        return f"script_alias_new_value_{self.hash}"

    def getCommandsText(self):
        if self.script is None:
            return ""
        return "\n".join(self.script.commands)

    def getVariablesJson(self):
        if self.script is None:
            return "[]"
        return json.dumps(
            [variable.to_dict() for variable in self.script.variables],
            ensure_ascii=False,
            indent=2,
        )

    def getVariableValue(self, variable):
        if variable.name in self.variable_values:
            return self.variable_values[variable.name]
        return variable.default if variable.default is not None else ""

    def getStates(self):
        if self.cmd_res is None:
            return []
        states = self.cmd_res.state[-20:]
        return [
            {
                "date": state.get("date"),
                "msg": state.get("msg", ""),
            }
            for state in states
        ]

    def getRunStates(self, run):
        return [
            {"date": state.get("date"), "msg": state.get("msg", "")}
            for state in run.result.state[-20:]
        ]

    def getRunVariables(self, run):
        # Historical runs keep the secrecy classification from their start.
        # The current definition alone may have removed or renamed a secret.
        historical_secret_names = getattr(run, "secret_variable_names", None)
        if historical_secret_names is None:
            # Older SDKs lack the snapshot, so secrecy is unknowable after an
            # edit. Mask every value until the SDK is upgraded.
            return [
                {"name": name, "value": "••••"}
                for name in run.result.variables
            ]
        secret_names = set(historical_secret_names) | {
            variable.name for variable in (self.script.variables if self.script else [])
            if variable.type == "secret"
        }
        return [
            {"name": name, "value": "••••" if name in secret_names else value}
            for name, value in run.result.variables.items()
        ]

    def formatDate(self, value):
        if value is None:
            return ""
        return value.strftime("%H:%M:%S")

    def formatRunStart(self, value):
        if value is None:
            return ""
        return value.strftime("%d.%m. %H:%M:%S")

    def buttons(self):
        buttons = {
            "tab_run": {
                "name": "tab_run",
                "params": {
                    "tab": "run",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.tab.run"),
                "button_active_condition": ("tab", "run"),
            },
            "tab_edit": {
                "name": "tab_edit",
                "params": {
                    "tab": "edit",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.tab.edit"),
                "button_active_condition": ("tab", "edit"),
            },
            "tab_schedule": {
                "name": "tab_schedule",
                "params": {
                    "tab": "schedule",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.tab.schedule"),
                "button_active_condition": ("tab", "schedule"),
            },
            "tab_aliases": {
                "name": "tab_aliases",
                "params": {
                    "tab": "aliases",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.tab.aliases"),
                "button_active_condition": ("tab", "aliases"),
            },
            "new": {
                "name": "new",
                "params": {
                    "tab": "edit",
                    "selected_script": NEW_SCRIPT,
                },
                "text": self.t("signaldeck_plugin_main.script.button.new"),
            },
            "refresh": {
                "name": "refresh",
                "params": {
                    "tab": "run",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.button.refresh"),
            },
        }

        if self.hasScript():
            start_params = {
                "start": True,
                "tab": "run",
                "selected_script": self.selected_script,
            }
            for variable in self.script.variables:
                start_params[variable.name] = f"@script_var_{variable.name}"

            buttons["start"] = {
                "name": "start",
                "params": start_params,
                "text": self.t("signaldeck_plugin_main.script.button.start"),
            }

            for run in self.runs:
                if run.status not in ("pending", "running"):
                    continue
                buttons[f"stop_run_{run.run_id}"] = {
                    "name": f"stop_run_{run.run_id}",
                    "params": {
                        "stop_run": True,
                        "run_id": run.run_id,
                        "tab": "run",
                        "selected_script": self.selected_script,
                    },
                    "text": self.t("signaldeck_plugin_main.script.button.stop"),
                }

        if self.hasScript():
            def schedule_params(key):
                return {
                    "save_schedule": True,
                    "tab": "schedule",
                    "selected_script": self.selected_script,
                    "schedule_cron": f"@script_schedule_cron_{key}",
                    "schedule_variables_json": f"@script_schedule_vars_{key}",
                    "schedule_enabled": f"@script_schedule_enabled_{key}",
                    "schedule_overlap": f"@script_schedule_overlap_{key}",
                }

            buttons["schedule_new"] = {
                "name": "schedule_new",
                "params": schedule_params("new"),
                "text": self.t("signaldeck_plugin_main.script.schedule.add"),
            }
            for schedule in self.schedules:
                key = schedule["id"]
                update = schedule_params(key)
                update["schedule_id"] = key
                buttons[f"schedule_save_{key}"] = {
                    "name": f"schedule_save_{key}",
                    "params": update,
                    "text": self.t("signaldeck_plugin_main.script.button.save"),
                }
                buttons[f"schedule_delete_{key}"] = {
                    "name": f"schedule_delete_{key}",
                    "params": {
                        "delete_schedule": True,
                        "schedule_id": key,
                        "tab": "schedule",
                        "selected_script": self.selected_script,
                    },
                    "text": self.t("signaldeck_plugin_main.script.schedule.delete"),
                }

        if self.script is not None:
            save_params = {
                "save": True,
                "tab": "edit",
                "selected_script": self.selected_script,
                "commands": "@script_commands",
                "variables_json": "@script_variables_json",
            }
            if self.isNewScript():
                save_params["new_script_name"] = "@script_name"

            buttons["save"] = {
                "name": "save",
                "params": save_params,
                "text": self.t("signaldeck_plugin_main.script.button.save"),
            }

        for index, alias in enumerate(self.aliases):
            buttons[f"save_alias_{index}"] = {
                "name": f"save_alias_{index}",
                "params": {
                    "save_alias": True,
                    "tab": "aliases",
                    "selected_script": self.selected_script,
                    "alias_name": alias.name,
                    "alias_value": f"@script_alias_value_{index}",
                },
                "text": self.t("signaldeck_plugin_main.script.button.save"),
            }

        buttons["save_alias_new"] = {
            "name": "save_alias_new",
            "params": {
                "save_alias": True,
                "tab": "aliases",
                "selected_script": self.selected_script,
                "alias_name": "@script_alias_new_name",
                "alias_value": "@script_alias_new_value",
            },
            "text": self.t("signaldeck_plugin_main.script.button.add"),
        }

        return buttons

    def getStatefullFields(self):
        return ["selected_script", "tab"]

    def getExportFields(self):
        return []
