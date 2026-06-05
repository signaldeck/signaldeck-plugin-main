from signaldeck_sdk import DisplayData
import json
import numpy as np

class ChartDisplayData(DisplayData):

    def __init__(self,ctx,actionHash,aggregationConfig):
        super().__init__(ctx, actionHash)
        self.aggregationConfig=aggregationConfig
        self.withCurrentButton=False
        self.currentValues = False
        self.lastN=None
        self.lastN_value=None
        self.optionsOrder=[]


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
        self.lastN_value=lastN
        return self

    def getDivID(self):
        return f'chart-{self.hash}'

    def isAggregation(self):
        return self.aggregationConfig is not None

    def getAggregationUnit(self):
        if not self.isAggregation():
            return ""
        return self.aggregationConfig.get("unit","day")

    def buttons(self) -> dict:
        newLastN = None
        if self.lastN == None:
            newLastN = self.lastN_value
        res= {
            "prev": {
                "name":"prev",
                "params":{"offset":self.offset+1},
                "text":self.ctx.t("signaldeck_plugin_main.chart.button.prev")
                },
            "next": {
                "name":"next",
                "params":{"offset":self.offset-1},
                "text":self.ctx.t("signaldeck_plugin_main.chart.button.next")},
            "lastN": {
                "name":"lastN",
                "params":{"lastN":newLastN},
                "text":self.ctx.t("signaldeck_plugin_main.chart.button.last_n"),
                "button_active_condition": ("lastN", self.lastN_value)
            },
            "currentValues": {
                "name":"currentValues",
                "params":{"offset":0,"currentValues":not self.currentValues},
                "text":self.ctx.t("signaldeck_plugin_main.chart.button.current_values"),
                "button_active_condition": ("currentValues", True)
            }  
        }
        if hasattr(self,"optionsOrder"):
            for option_row in self.optionsOrder:
                for optionName in option_row["options"]:
                    res[optionName] = {
                        "name": optionName,
                        "text": self.options[optionName].get("display_name", optionName),
                        "button_active_condition": ("option", optionName),
                        "params": {"option": optionName}
                    }
        return res

    
    def showButton(self,name):
        if self.aggregationConfig is not None:
            return False
        if name == "lastN":
            return self.withLastButton
        if name == "currentValues":
            return self.withCurrentButton
        return True

    def getExportFields(self):
        return {}
    
    def getStatefullFields(self):
        return ["offset", "option", "lastN"]
    
    def withOptions(self,optionsOrder,options):
        self.optionsOrder=optionsOrder
        self.options=options
        if len(optionsOrder) > 0:
            if not hasattr(self, "option") or not self.option:
                self.option= optionsOrder[0]["options"][0]
            o = self.options.get(self.option)
            self.withLabel(o.get("title","")) 
            self.withUnit(o.get("unit","")) 
            self.withLastNOption(o.get("lastN",None))
            self.withYMinMax(o.get("y-range",{}).get("min",None),o.get("y-range",{}).get("max",None)) 
            self.withPlotType(o.get("type","scatter")) 
            self.withCurrentOption(o.get("withCurrent",False))
        return self