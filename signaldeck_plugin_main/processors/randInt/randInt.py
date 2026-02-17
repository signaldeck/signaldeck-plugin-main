from signaldeck_sdk import Processor
from threading import Thread
from random import randint
import logging 
import time

def genInt(inst):
    while inst.is_running:
        if inst.continue_update():   
            newValue = randint(0,100)
            while newValue == inst.value:
                newValue = randint(0,100)
            inst.logger.info("New value: "+str(newValue))
            inst.value=newValue
        time.sleep(1)


class randInt(Processor):
    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.value=10
        self.logger = logging.getLogger(__name__)
        self.start()

    def continue_update(self):
        return self.continue_max() and self.continue_min()
    
    def continue_max(self):
        if not hasattr(self,"stopHigh"):
            return True
        return self.value <= self.stopHigh
    
    def continue_min(self):
        if not hasattr(self,"stopLow"):
            return True
        return self.value >= self.stopLow


    def start(self):
        self.is_running=True
        self.thread=  Thread(target=genInt, args=[self])
        self.thread.daemon = True
        self.thread.start()

    def __del__(self):
        self.logger.warn("beeing killedd")
        self.is_running=False
        self.thread.join()

    def double_me(self,val,offset=0):
        return 2*val + offset

    def process(self,value,actionHash,file=None):
        return {"data":{"value":value}}