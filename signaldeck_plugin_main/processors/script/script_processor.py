import json
import logging

from signaldeck_sdk import Cmd, DisplayProcessor, ScriptDefinition

from .script_display_data import NEW_SCRIPT, ScriptDisplayData


class ScriptProcessor(DisplayProcessor):
    def __init__(self, name, config, ctx, vP, collect_data):
        super().__init__(name, config, ctx, vP, collect_data)
        self.logger = logging.getLogger(__name__)
        self.cmd: Cmd | None = None

    def registerCommands(self, cmd: Cmd):
        self.cmd = cmd

    def getTemplate(self, value):
        return "main/script.html"

    def getAdditionalJsFiles(self, value):
        return [("main", "js/script.js")]

    def getAdditionalCssFiles(self, value):
        return [("main", "css/script.css")]

    def getJS_functions_to_call_on_client(self, data: ScriptDisplayData):
        return {data.getSelectId(): "initScriptSelect"}

    def _initial_script_name(self, value):
        if isinstance(value, list):
            value = value[0] if value else None
        if value in (None, "", "*"):
            return None
        return str(value)

    def _resolve_selection(self, value, **kwargs):
        selected = kwargs.get("selected_script")
        if kwargs.get("save") and selected == NEW_SCRIPT:
            new_name = str(kwargs.get("new_script_name", "")).strip()
            if new_name:
                return new_name

        if selected:
            return selected

        initial = self._initial_script_name(value)
        if initial and self.cmd.getScript(initial) is not None:
            return initial

        scripts = self.cmd.listScripts()
        return scripts[0].name if scripts else None

    def _script_variables_from_kwargs(self, script, kwargs):
        values = {}
        if script is None:
            return values
        for variable in script.variables:
            if variable.name in kwargs:
                values[variable.name] = kwargs[variable.name]
            elif variable.default is not None:
                values[variable.name] = variable.default
        return values

    def _parse_commands(self, text):
        return [line.strip() for line in str(text or "").splitlines() if line.strip()]

    def _parse_variables(self, text):
        raw = json.loads(text or "[]")
        if not isinstance(raw, list):
            raise ValueError("Script variables must be a JSON list")
        return raw

    def performActions(self, value, actionHash, **kwargs):
        if self.cmd is None:
            raise RuntimeError("Cmd is not registered")

        selected = kwargs.get("selected_script")

        if "start" in kwargs:
            script = self.cmd.getScript(selected)
            if script is None:
                raise ValueError(f"{selected} is not a known script")
            variables = self._script_variables_from_kwargs(script, kwargs)
            self.cmd.runScript(selected, **variables)

        if "stop" in kwargs and selected:
            self.cmd.stop(selected)

        if "save" in kwargs:
            name = selected
            if selected == NEW_SCRIPT:
                name = str(kwargs.get("new_script_name", "")).strip()
            if not name:
                raise ValueError("Script name must not be empty")

            script = ScriptDefinition.from_dict({
                "name": name,
                "commands": self._parse_commands(kwargs.get("commands", "")),
                "variables": self._parse_variables(kwargs.get("variables_json", "[]")),
            })
            self.cmd.saveScript(script)

    def getDisplayData(self, value, actionHash, **kwargs):
        if self.cmd is None:
            raise RuntimeError("Cmd is not registered")

        selected = self._resolve_selection(value, **kwargs)
        tab = kwargs.get("tab", "run")

        script = None
        cmd_res = None
        if selected == NEW_SCRIPT:
            script = ScriptDefinition(name="", commands=[], variables=[])
            tab = "edit"
        elif selected:
            script = self.cmd.getScript(selected)
            cmd_res = self.cmd.current.get(selected)

        variable_values = self._script_variables_from_kwargs(script, kwargs)

        return (
            ScriptDisplayData(self.ctx, actionHash)
            .withScripts(self.cmd.listScripts())
            .withSelection(selected, tab)
            .withScript(script)
            .withCmdResult(cmd_res)
            .withVariableValues(variable_values)
            .withNewScriptName(kwargs.get("new_script_name", ""))
        )

    def getBoolParams(self):
        return ["start", "stop", "save"]

    def getIntParams(self):
        return []

    def getFloatParams(self):
        return []
