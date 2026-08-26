import json

from signaldeck_sdk import DisplayData


NEW_SCRIPT = "__new__"


class ScriptDisplayData(DisplayData):
    def __init__(self, ctx, action_hash):
        super().__init__(ctx, action_hash)
        self.scripts = []
        self.commands = []
        self.selected_script = None
        self.tab = "run"
        self.script = None
        self.cmd_res = None
        self.variable_values = {}
        self.new_script_name = ""

    def withScripts(self, scripts):
        self.scripts = scripts
        return self

    def withCommands(self, commands):
        self.commands = commands
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

    def formatDate(self, value):
        if value is None:
            return ""
        return value.strftime("%H:%M:%S")

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
            "tab_commands": {
                "name": "tab_commands",
                "params": {
                    "tab": "commands",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.tab.commands"),
                "button_active_condition": ("tab", "commands"),
            },
            "new": {
                "name": "new",
                "params": {
                    "tab": "edit",
                    "selected_script": NEW_SCRIPT,
                },
                "text": self.t("signaldeck_plugin_main.script.button.new"),
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
            buttons["stop"] = {
                "name": "stop",
                "params": {
                    "stop": True,
                    "tab": "run",
                    "selected_script": self.selected_script,
                },
                "text": self.t("signaldeck_plugin_main.script.button.stop"),
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

        return buttons

    def getStatefullFields(self):
        return ["selected_script", "tab"]

    def getExportFields(self):
        return []
