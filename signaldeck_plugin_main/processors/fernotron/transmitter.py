import subprocess
import time
from signaldeck_sdk import Processor
from signaldeck_sdk import Cmd, Command

class FernotronTransmitter(Command):
    def __init__(self,processor):
        self.processor=processor
        super().__init__("fernotron","Send fernotron command")

    async def run(self, fernValue,count,cmdRes=None,stopEvent=None):
        self.processor.process(fernValue,None,count=count)
        if cmdRes is not None:
            cmdRes.appendState(self,msg=f'Send fernotron code {fernValue}')

class transmitter(Processor):

    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.command=config["command"]

    def process(self,value, actionHash,file=None,count=20):
        proc = subprocess.Popen([self.command, value,str(count)], stdout=subprocess.PIPE)
        out, err = proc.communicate()
        print(out.decode('utf-8'))
        print(self.command+" "+ value)
        #Make sure not to mix signals
        time.sleep(1)

    def registerCommands(self, cmd: Cmd):
        cmd.registerCmd(FernotronTransmitter(self))