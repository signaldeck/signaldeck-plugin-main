from signaldeck_sdk import Processor
import logging, subprocess, json, datetime

DATE_MACRO="{date}"

class RClone(Processor):
    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.command=self.config.get("rclone_command",["rclone","rcat"])
        self.logger=logging.getLogger(__name__)

    def process(self,value,actionHash,file=None):
        values=value.split(",")
        processorName= values[0]
        actionValue= values[1]
        dest=values[-1].replace(DATE_MACRO,str(datetime.datetime.now().date()).replace("-","_"))
        params={}
        if len(values) > 3:
            redValues=values[2:-1]
            for val in redValues:
                key, v = val.split(":")
                params[key]=v
        processorInst = self.valueProvider.processors[processorName]
        data = processorInst.process(actionValue,"dummyhash",**params)
        if data is None or "data" not in data:
            return
        data=data["data"]
        res = subprocess.run(self.command+[dest], input=str.encode(json.dumps(data,default=str)))
        self.logger.info(res.returncode)
        return {"html":"","data":{"returncode":res.returncode}}