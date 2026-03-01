import datetime
from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData, Placeholder
from signaldeck_sdk.persistence.persist_data import PersistData
from .dummy_display_data import DummyDisplayData


def days_between(start: datetime, end: datetime) -> float:
    """
    Gibt die Anzahl der Tage zwischen zwei datetime-Objekten als Float zurück.
    Positive Zahl, wenn end nach start liegt.
    """
    delta = end - start
    return delta.total_seconds() / 86400.0

def getDateFromString(dateStr, dateFormat):
    if dateStr.lower() == "$now$":
        return datetime.datetime.now()
    try:
        return datetime.datetime.strptime(dateStr, dateFormat)
    except Exception as e:
        raise ValueError(f"Date string '{dateStr}' does not match format '{dateFormat}'") from e

def calc_hist(cur_val,type,perDay=1,days=1):
    if type == "asc":
        res = cur_val - perDay * days
    else:
        res = cur_val + perDay * days
    return res

class Data(PersistData,DisplayProcessor):

    hist_per_day_fields=[]

    def __init__(self,name,config,valueProvider,collect_data):
        super().__init__(name,config,valueProvider,collect_data)
        self.hist_config = dict(self.config.get("hist",{}))
        for n, v in self.getValues().items():
            setattr(self,n,v)
        for field, val in self.hist_config.items():
            if "perDay" in val.keys():
                self.hist_per_day_fields.append(f'{field}_change_per_day')

    @classmethod
    def config_placeholders(cls):
        return [Placeholder("DATE_FORMAT", "Date format?", "str", default= "%d.%m.%Y %H:%M:%S")]

    def getTemplate(self, value):
        return "main/dummy_data.html"  

    def getDisplayData(self, value, actionHash, **kwargs) -> DisplayData:
        return DummyDisplayData(self.ctx, actionHash).withData(self.getValues()).withHistConfig(self.hist_config)

    def performActions(self, value, actionHash, **kwargs):
        for k, v in kwargs.items():
            if k.endswith("change_per_day"):
                self.hist_config[k.split("_change_per")[0]]["perDay"]=v
            else:
                setattr(self, k, v)
        print(kwargs)
        print(self.hist_config)

    def getValues(self):
        res={}
        for n in self.getBoolParams()+self.getIntParams()+self.getFloatParams():
            if not n.endswith("change_per_day"):
                res[n] = getattr(self,n,self.config.get("defaults",{}).get(n,None))
        for n in self.getDateParams():
            tres = getattr(self,n,self.config.get("defaults",{}).get(n,None))
            if isinstance(tres,str):
                tres = getDateFromString(tres,self.config.get("date_format","%d.%m.%Y %H:%M:%S"))
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
        return self.config.get("vars",{}).get("float",[]) + self.hist_per_day_fields

    def hist(self,fieldName,config=None,days=1,date=None,first=False,last=False,dropna=True,fullDay=False,recursive=True,current=False,currentValues=False,**kwargs):
        res = self.getValue(fieldName)
        hist_config = self.config.get("hist",{}).get(fieldName,None)
        self.logger.info(f"Calculating history for field {fieldName} with config {hist_config} and params days={days}, date={date}, first={first}, last={last}, dropna={dropna}, fullDay={fullDay}, recursive={recursive}, current={current}, currentValues={currentValues}")
        if hist_config is None:
            return res
        if date is None:
            date = datetime.datetime.now() + datetime.timedelta(days=-days)
        if last:
            if days>0:
                date=date.replace(hour=23,minute=59,second=59)
        if first:
            date=date.replace(hour=0,minute=0,second=0)
        floatDays = -days_between(datetime.datetime.now(), date)

        if hist_config.get("type") == "asc" or hist_config.get("type") == "desc":
             res = calc_hist(res,hist_config.get("type"),hist_config.get("perDay",1),days = floatDays)
        self.logger.info(f"Calculated history value for field {fieldName}: {res}")
        return res