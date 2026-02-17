import datetime
from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData
from processors.dummy_data.dummy_display_data import DummyDisplayData

class Data(DisplayProcessor):
    def __init__(self,name,config,valueProvider,collect_data):
        super().__init__(name,config,valueProvider,collect_data)
        for n, v in self.getValues().items():
            setattr(self,n,v)

    def getTemplate(self, value):
        return "main/dummy_data.html"  

    def getDisplayData(self, value, actionHash, **kwargs) -> DisplayData:
        for k in kwargs.keys():
            val=kwargs[k]
            if k in self.getDateParams():
                val=datetime.datetime.strptime(val,self.config.get("date_format"))
            setattr(self,k,val)
        return DummyDisplayData(actionHash,self.getValues())

    def getValues(self):
        res={}
        print(self.config)
        for n in self.getBoolParams()+self.getIntParams()+self.getFloatParams():
            res[n] = getattr(self,n,self.config.get("defaults",{}).get(n,None))
        for n in self.getDateParams():
            tres = getattr(self,n,self.config.get("defaults",{}).get(n,None))
            if isinstance(tres,str):
                tres = datetime.datetime.strptime(tres,self.config.get("date_format"))
            res[n]=tres
        print(res)
        return res

    def getValNames(self):
        return self.getBoolParams()+self.getIntParams()+self.getFloatParams()+self.getDateParams()

    def getDateParams(self):
        return self.config.get("vars",{}).get("date",[])

    def getBoolParams(self):
        return self.config.get("vars",{}).get("bool",[])

    def getIntParams(self):
        return self.config.get("vars",{}).get("int",[])

    def getFloatParams(self):
        return self.config.get("vars",{}).get("float",[])
