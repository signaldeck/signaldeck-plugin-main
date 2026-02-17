import logging
import numpy as np
import os
from signaldeck_sdk import Processor
from flask import render_template
import datetime
import paho.mqtt.client as mqtt 
from pathlib import Path
import json
from jsonpath_ng import jsonpath, parse
import time
import pandas as pd
import datetime
from signaldeck_sdk import Cmd, Command



class HC_Pause(Command):
    def __init__(self,processor):
        self.processor=processor
        super().__init__("home_connect_pause","Pause home connect device. Only available on washing machines. Args: hci (Home Connect ID)")

    async def run(self, hcid, *args ,cmdRes=None,stopEvent=None):
        if not self._finished or stopEvent.is_set():
            cmdRes.appendState(self,msg=f'Unable')
            return
        cmdRes.appendState(self,msg=f'Successfully')
        


class HC_Resume(Command):
    def __init__(self,processor):
        self.processor=processor
        super().__init__("home_connect_resume","Resume home connect device. Only available on washing machines. Args: hci (Home Connect ID)")

    async def run(self, hcid, *args ,cmdRes=None,stopEvent=None):
        if not self._finished or stopEvent.is_set():
            cmdRes.appendState(self,msg=f'Unable')
            return
        cmdRes.appendState(self,msg=f'Successfully')
        


class HC_Start(Command):
    def __init__(self,processor):
        self.processor=processor
        super().__init__("home_connect_start","Starts currently set program. Args: hci (Home Connect ID)")

    async def run(self, hcid, *args ,cmdRes=None,stopEvent=None):
        if not self._finished or stopEvent.is_set():
            cmdRes.appendState(self,msg=f'Unable')
            return
        cmdRes.appendState(self,msg=f'Successfully')
        



class home_connect_client(Processor):

    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.logger = logging.getLogger(__name__)

        

    def registerCommands(self, cmd: Cmd):
        self.cmd = cmd
        cmd.registerCmd(HC_Pause(self))
        cmd.registerCmd(HC_Resume(self))
        cmd.registerCmd(HC_Start(self))


    def process(self,value,actionHash,file=None):
        #value is topic
        return {"html": self.getState([value],actionHash),"data":self.currentVals[value]}


    def getState(self,value,actionHash):
        value=value[0]
        if self.currentVals[value] is None:
            return ""
        if "render_state" in self.topicConfig[value]:
            return render_template(self.topicConfig[value]["render_state"],values=self.currentVals[value],i18n=i18nFromMapping(self.topicConfig[value]["mapping"]))
        return self.currentVals[value]