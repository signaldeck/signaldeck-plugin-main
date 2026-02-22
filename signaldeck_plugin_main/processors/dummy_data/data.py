import datetime
from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData, Placeholder
from signaldeck_sdk.persistence.persist_data import PersistData
from .dummy_display_data import DummyDisplayData


class Data(PersistData,DisplayProcessor):
    def __init__(self,name,config,valueProvider,collect_data):
        super().__init__(name,config,valueProvider,collect_data)
        for n, v in self.getValues().items():
            setattr(self,n,v)

    @classmethod
    def config_placeholders(cls):
        return [Placeholder("DATE_FORMAT", "Date format?", "str", default= "%d.%m.%Y %H:%M:%S")]

    def getTemplate(self, value):
        return "main/dummy_data.html"  

    def getDisplayData(self, value, actionHash, **kwargs) -> DisplayData:
        return DummyDisplayData(self.ctx, actionHash).withData(self.getValues())

    def performActions(self, value, actionHash, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def getValues(self):
        res={}
        for n in self.getBoolParams()+self.getIntParams()+self.getFloatParams():
            res[n] = getattr(self,n,self.config.get("defaults",{}).get(n,None))
        for n in self.getDateParams():
            tres = getattr(self,n,self.config.get("defaults",{}).get(n,None))
            if isinstance(tres,str):
                tres = datetime.datetime.strptime(tres,self.config.get("date_format"))
            res[n]=tres
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

    def hist(self,fieldName,config=None,days=1,date=None,first=False,last=False,dropna=True,fullDay=False,recursive=True,current=False,currentValues=False,**kwargs):
        return self.getValues().get(fieldName,0)