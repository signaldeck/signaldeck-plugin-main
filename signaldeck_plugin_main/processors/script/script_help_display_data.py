from signaldeck_sdk import ConditionCommand, DisplayData


class ScriptHelpDisplayData(DisplayData):
    def __init__(self, ctx, action_hash):
        super().__init__(ctx, action_hash)
        self.commands = []
        self.tab = "language"

    def withCommands(self, commands):
        self.commands = commands
        return self

    def withTab(self, tab):
        self.tab = tab if tab in ("language", "commands") else "language"
        return self

    def isConditionCommand(self, command):
        return isinstance(command, ConditionCommand)

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
        }

    def getStatefullFields(self):
        return ["tab"]

    def getExportFields(self):
        return []
