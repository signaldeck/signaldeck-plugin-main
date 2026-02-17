from signaldeck_sdk import DisplayData
import json
import numpy as np

class ChartDisplayData(DisplayData):

    def __init__(self,actionHash,aggregationConfig):
        super().__init__(actionHash)
        self.aggregationConfig=aggregationConfig
        self.withCurrentButton=False


    def withCurrentOption(self,enable=True):
        self.withCurrentButton=enable
        return self

    def withYValues(self, yVals):
        self.yVals =  [
            v.item() if isinstance(v, np.generic) else v
            for v in yVals
        ]
        return self

    def withXValues(self, xVals):
        self.xVals = xVals
        return self

    def withUnit(self,unit):
        self.unit=unit
        return self
    
    def withPlotType(self,type):
        self.type=type
        return self

    def withLabel(self,label):
        self.label=label
        return self
    
    def withDate(self,date):
        self.date=date
        return self

    def withYMinMax(self, ymin,ymax):
        self.ymin =str(ymin)
        self.ymax =str(ymax)
        return self
    


    def withLastNOption(self,lastN):
        self.withLastButton=False
        if lastN is None:
            return self
        self.withLastButton=True
        self.lastN=lastN
        return self

    def getDivID(self):
        return f'chart-{self.hash}'

    def isAggregation(self):
        return self.aggregationConfig is not None

    def getAggregationUnit(self):
        if not self.isAggregation():
            return ""
        return self.aggregationConfig.get("unit","day")

    def getStateChangeButtonData(self):
        if self.aggregationConfig is not None:
            return []
        res= [{"name":"prev","id":"prev"+self.hash,"actionhash":self.hash,"get_params":json.dumps({"offset":self.offset+1}),"text":"<"},
        {"name":"next","id":"next"+self.hash,"actionhash":self.hash,"get_params":json.dumps({"offset":self.offset-1}),"text":">"}]
        if self.withLastButton:
            res.append({"name":"lastN","id":"lastN"+self.hash,"actionhash":self.hash,"get_params":json.dumps({"offset":self.offset,"lastN":self.lastN}),"text":"letzte"})
        if self.withCurrentButton:
            res.append({"name":"currentValues","id":"currentValues"+self.hash,"actionhash":self.hash,"get_params":json.dumps({"offset":0,"currentValues":True}),"text":"memory"})
        return res

    def getExportFields(self):
        return {}