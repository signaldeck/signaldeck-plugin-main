import logging
from signaldeck_sdk import Processor
import datetime
import paho.mqtt.client as mqtt 
from pathlib import Path
import json
from jsonpath_ng import parse
import time
import pandas as pd
import datetime
from signaldeck_sdk import Cmd, Command
import threading
from collections import deque
from signaldeck_sdk import PersistData
from zoneinfo import ZoneInfo 

class TasmotaCommand(Command):
    def __init__(self,processor):
        self.processor=processor
        super().__init__("tasmotaCmd","Tasmota command. Args: topic command (payload)")

    def processResult(self,message):
        print(message.payload.decode("utf-8"))
        self._finished=True
        self.processor.client.unsubscribe(message.topic)
        del self.processor.redirect[message.topic]

    def _run(self,fullTopic,resultTopic,payload):
        self.processor.client.subscribe(resultTopic)
        self.processor.client.publish(fullTopic,payload)

    async def run(self, topic,command, *args ,cmdRes=None,stopEvent=None):
        fullTopic = f'cmnd/{topic}/{command}'
        resultTopic = f'stat/{topic}/RESULT'
        payload = None
        if len(args) > 0:
            payload = str(args[0])
        self.processor.redirect[resultTopic]=self.processResult
        self._finished=False
        thr = threading.Thread(target= self._run, args=(fullTopic,resultTopic,payload))
        thr.start()
        counter=0
        while not self._finished and counter < 30 and not stopEvent.is_set():
            time.sleep(1)
            counter+=1
        if not self._finished or stopEvent.is_set():
            cmdRes.appendState(self,msg=f'Unable to perform command {fullTopic} {payload}!')
            return
        cmdRes.appendState(self,msg=f'Successfully performed command {fullTopic} {payload}')
        


def i18nFromMapping(mapping):
    res={}
    for field in mapping:
        res[field["name"]]=field["displayName"]
    return res

def creatDirIfNeeded(t):
    if t is None:
        return
    if not Path(t["dir"]).exists():
        Path(t["dir"]).mkdir(parents=True,exist_ok=True)

def classFromName(classPath):
  className=classPath.split(".")[-1]
  path=classPath[:-(len(className)+1)]
  mod=__import__(path,fromlist=[className])
  return getattr(mod,className)

class mqtt_subscriber(PersistData,Processor):

    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.logger = logging.getLogger(__name__)
        self.topicConfig=config["topics"]
        for topic in self.topicConfig.keys():
            self.topicConfig[topic]["processor_name"]=self.name+f":{topic}"
        self.topics=[]
        if collect_data:
            self.client = mqtt.Client()
            if "client_class" in config and config["client_class"] is not None:
                self.client =classFromName(config["client_class"])()
            self.client.enable_logger(self.logger)     
            self.client.suppress_exceptions = True        
            self.client.reconnect_delay_set(1, 120)
            self.client.on_connect = self.on_connect
            self.client.on_message=self.on_message 
            self.client.on_disconnect=self.on_disconnect
            self.client.connect(config["host"]) 
            self.client.loop_start()
        self.redirect={}
        self._last_action_time={}
        self.temp_data={}
        self.memory: dict[str, deque] = {}
        
    def _getRequiredDataStores(self,config=None):
        if not config:  
            config=self.config
        seen = set()
        res=[]
        topics = config.get("topics",{})
        for topic, topic_cfg in topics.items():
            if "persist" in topic_cfg:
               for e in super()._getRequiredDataStores(config=topic_cfg):
                    if e not in seen:
                        seen.add(e)
                        res.append(e)
        return res
    

    def init_current_vals(self,config=None):
        if not config:  
            config=self.config
        topics = config.get("topics",{})
        for topic, topic_cfg in topics.items():
            data = super().init_current_vals(topic_cfg)
            if data:
                self.currentVals[topic] = data


    def shutdown(self):
        self.logger.info("Shutdown mqtt client")
        if self.collect_data:
            self.client.disconnect()
            self.client.loop_stop()  



    def registerCommands(self, cmd: Cmd):
        self.cmd = cmd
        cmd.registerCmd(TasmotaCommand(self))

    def on_connect(self,client, userdata, flags, rc):
        for t in self.topicConfig:
            self.registerTopic(t)

    def on_disconnect(self,client, userdata, rc, properties=None):
        """
        Wird bei jeder Trennung aufgerufen.
        rc == 0  → freiwillig (client.disconnect())
        rc != 0  → unerwartet (Netzwerkproblem, Broker down, Keep-Alive überschritten …)
        """
        self.logger.warning("Disconnect (rc = %s)" % rc)

        if rc != 0:
            # ► Automatisch reconnecten …
            self.logger.warning("Unerwartete Trennung – versuche Wiederverbindung in 5 s")
            time.sleep(5)
            try:
                client.reconnect()
            except Exception as err:
                print("Reconnect schlug fehl:", err)

    def getDfFromMemory(self,topic,fieldName,dateField):
        if topic not in self.memory:
            return None
        res = pd.DataFrame(list(self.memory[topic]))
        res=res.set_index(dateField)
        return res[fieldName]


    def getDateFieldName(self,config):
        for f in config.get("mapping"):
            if f["type"] == "date":
                return f["name"]

    def getCurFieldValue(self,fieldName,**kwargs):
        topic = kwargs["topicname"]
        return self.currentVals[topic][fieldName]

    def hist(self,topic,fieldName,date=None,days=1,recursive=True,currentValues=False,**params):
        if currentValues:
            return self.getDfFromMemory(topic,fieldName,self.getDateFieldName(self.topicConfig[topic]))
        res= super().hist(fieldName,config=self.topicConfig[topic],date=date,days=days,**params,recursive=False,currentValues=False,topicname=topic)
        return res

    def getDateFormat(self,config=None):
        return "%Y-%m-%dT%H:%M:%S"

    def getValue(self,fieldName):
        parts= fieldName.rsplit(":",1)
        topic=parts[0]
        field=parts[1]
        if self.currentVals[topic] is None:
            return None
        return self.currentVals[topic][field]
        
    
    def _registerFieldsForDataStores(self):
        print(f'Topics: {self.topics}')
        for topic in self.topicConfig.keys():
            for dataStoreName in self.dataStores:
                for persistConfig in self.topicConfig[topic].get("persist",[]):
                    if persistConfig["type"] != dataStoreName:
                        continue
                    fields = self.getFields(config=persistConfig,postfix_name=f":{topic}")
                    if fields is None:
                        self.logger.warning(f'No fields defined for processor {self.name}, cannot register data store {dataStoreName}!')
                        continue
                    self.logger.info(f'Registering fields for data store {dataStoreName} and processor {self.name}: {fields}')
                    for field in fields:
                        self.dataStores[dataStoreName].register_field(field)
    
    
    def setCurVal(self,curVal,config=None):
        pass #We handle it outside

    def makeDataAvailable(self,config=None):
        pass

    def process(self,value,actionHash,file=None):
        if value.startswith("reset:"):
            topic = value[len("reset:"):]
            self.memory.pop(topic, None)
            return {"html": self.getState([topic],actionHash),"data":self.currentVals[topic]}
        #value is topic
        return {"html": self.getState([value],actionHash),"data":self.currentVals[value]}



    def saveTopic(self,topic):
        config=self.topicConfig[topic]
        values=self.currentVals[topic]
        self.logger.debug(f'New data for topic "{topic}": {values}')
        prev_values = self.prev_curVal.get(topic, None)
        if topic not in self.memory:
            maxlen = config.get("cacheSize",1000)
            self.memory[topic] = deque(maxlen=maxlen)
        self.memory[topic].append(values)
        self.save_data(values, prev_data= prev_values,config=config)
        

    def on_message(self,client, userdata, message):
        try:
            self.logger.debug("received:" +str(message.topic))
            if message.topic in self.redirect:
                self.redirect[message.topic](message)
                return
            resJson= message.payload.decode("utf-8")
            json_data = json.loads(resJson)
            res={}
            mapping = self.topicConfig[message.topic]["mapping"]
            for mappingElement in mapping:
                if mappingElement.get("type","") == "date" and mappingElement.get("jsonPath","") == "now":
                    res[mappingElement["name"]]= datetime.datetime.now(ZoneInfo(mappingElement.get("timezone","Europe/Berlin")))
                    continue
                jsonpath_expression = parse(mappingElement["jsonPath"])
                match = jsonpath_expression.find(json_data)
                if len(match)>0:
                    res[mappingElement["name"]]=match[0].value
            if len(res) < len(mapping):
                #We only have a subset. Hold the value in memory and wait for missing fields
                if not message.topic in self.temp_data:
                    self.temp_data[message.topic]={}
                if "total_in" in res.keys():
                    self.temp_data[message.topic]={}
                for newKey in res.keys():
                    self.temp_data[message.topic][newKey]=res[newKey]
            else:
                self.temp_data[message.topic]=res
            if len(self.temp_data[message.topic]) == len(mapping):
                self.prev_curVal[message.topic]=self.currentVals[message.topic]
                self.currentVals[message.topic]= self.temp_data[message.topic]
                self.temp_data[message.topic]={}
                self.handleTypes(message.topic)
                self.saveTopic(message.topic)
                
                
        except Exception:
            self.logger.exception("on_message() abgebrochen – Topic %s", message.topic, exc_info=True)

    def handleTypes(self,topic):
        tConfig = self.topicConfig[topic]
        for field in tConfig["mapping"]:
            if "type" not in field:
                continue
            if field["type"]=="date" and isinstance(self.currentVals[topic][field["name"]],str):
                if "date_format" in field:
                    if field["date_format"]=="ts":
                        self.currentVals[topic][field["name"]]= datetime.datetime.fromtimestamp(self.currentVals[topic][field["name"]])
                    else:
                        self.currentVals[topic][field["name"]]= datetime.datetime.strptime(self.currentVals[topic][field["name"]],field["date_format"])
                else:
                    self.currentVals[topic][field["name"]]= datetime.datetime.fromisoformat(self.currentVals[topic][field["name"]])


    def registerTopic(self,topic):
        self.topics.append(topic)
        self.logger.info("Register for topic: "+topic)
        self.client.subscribe(topic)
        self.currentVals[topic]=None
        

    def getState(self,value,actionHash):
        value=value[0]
        if value.startswith("reset:"):
            return ""
        if self.currentVals[value] is None:
            return ""
        if "render_state" in self.topicConfig[value]:
            return self.ctx.render(self.topicConfig[value]["render_state"],values=self.currentVals[value],i18n=i18nFromMapping(self.topicConfig[value]["mapping"]))
        return self.currentVals[value]