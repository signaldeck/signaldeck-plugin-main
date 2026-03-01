from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData
import logging, json
from signaldeck_sdk import Cmd
from signaldeck_sdk import CmdResult

class CmdDisplayData(DisplayData):
    def __init__(self,ctx, hash,params):
        super().__init__(ctx, hash)
        self.cmd:Cmd=None
        self.currParams=params
    
    def withCmdRes(self,cmdRes: CmdResult):
        self.cmdRes=cmdRes
        return self

    def buttons(self):
        return {"start":{"name":"start","params":{"start":1},"text":self.ctx.t("signaldeck_plugin_main.cmd.button.start")},
                "stop":{"name":"stop","params":{"stop":1},"text":self.ctx.t("signaldeck_plugin_main.cmd.button.stop")}}

    def getCSSClass(self,buttonName):
        if buttonName == "start" and self.cmdRes is not None and not self.cmdRes.isFinished():
            return " hide"
        if buttonName == "stop" and self.cmdRes is not None and self.cmdRes.isFinished():
            return " hide"
        return ""
    

    def formatDate(self, d):
        return d.strftime("%H:%M:%S")
    
    def getStates(self):
        if self.cmdRes is None:
            return []
        states=self.cmdRes.state#[s for s in self.cmdRes.state if s["command"]=="echo"]
        if len(states) > 10:
            states=states[-10:]
        return [{"date":s["date"],"msg":s["msg"]} for s in states]
    
    def getExportFields(self):
        return []

class CmdProcessor(DisplayProcessor):
    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.logger = logging.getLogger(__name__)

    def getDisplayData(self,value,actionHash,**kwargs):
        res = CmdDisplayData(self.ctx, actionHash,params=kwargs)
        scriptName = value
        if type(scriptName) is list:
            scriptName = scriptName[0]
        res.withCmdRes(self.cmd.current.get(scriptName,None))
        return res
    
    def providesState(self,value):
        return not value[0].startswith("start_")

    def performActions(self,value,actionHash,**kwargs):
        if "start" in kwargs:
            self.cmd.runScript(value)
        if "stop" in kwargs:
            self.cmd.stop(value)
        if value.startswith("start_"):
            scriptName=value[6:]
            self.cmd.runScript(scriptName)
        return

    def getTemplate(self,value):
        return "main/cmd.html"
    
    def registerCommands(self, cmd: Cmd):
        self.cmd=cmd

    def getBoolParams(self):
        return []

    def getIntParams(self):
        return []
    
    def getFloatParams(self):
        return []