from signaldeck_sdk import ConditionCommand, DisplayData, ValueCommand


class ScriptHelpDisplayData(DisplayData):
    def __init__(self, ctx, action_hash):
        super().__init__(ctx, action_hash)
        self.commands = []
        self.values = []
        self.methods = []
        self.tab = "language"

    def withCommands(self, commands):
        self.commands = commands
        return self

    def withValueProvider(self, values, methods):
        self.values = values
        self.methods = methods
        return self

    def withTab(self, tab):
        self.tab = tab if tab in ("language", "commands", "value_provider") else "language"
        return self

    def isConditionCommand(self, command):
        return isinstance(command, ConditionCommand)

    def isValueCommand(self, command):
        return isinstance(command, ValueCommand)

    def buttons(self):
        return {
            "tab_language": {
                "name": "tab_language",
                "params": {"tab": "language"},
                "text": self.t("signaldeck_plugin_main.script.help.tab.language"),
                "button_active_condition": ("tab", "language"),
            },
            "tab_commands": {
                "name": "tab_commands",
                "params": {"tab": "commands"},
                "text": self.t("signaldeck_plugin_main.script.tab.commands"),
                "button_active_condition": ("tab", "commands"),
            },
            "tab_value_provider": {
                "name": "tab_value_provider",
                "params": {"tab": "value_provider"},
                "text": "ValueProvider",
                "button_active_condition": ("tab", "value_provider"),
            },
        }

    def getStatefullFields(self):
        return ["tab"]

    def getExportFields(self):
        return []
