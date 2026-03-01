from signaldeck_sdk import DisplayData


class DummyDisplayData(DisplayData):

    def withData(self,data):
        self.values= data
        return self
    
    def withHistConfig(self,hist_config):
        self.hist_config = hist_config
        return self

    def getValues(self):
        return self.values
    
    def getValue(self,name):
        return self.values.get(name,None)
    
    
    def getExportFields(self):
        return []
    
    def hasPerDayField(self,field):
        return "perDay" in self.hist_config.get(field,{}).keys()
    
    def getChangePerDayValue(self,field):
        return self.hist_config.get(field,{}).get("perDay", None)
    

    def buttons(self):
        res = {}
        for key in self.values.keys():
            newButton = {"name": key, "text": "save", "params": {key: "@"+key+"_field"}}
            res[key] = newButton
        for key, val in self.hist_config.items():
            if "perDay" in val.keys():
                newButton = {"name": f'{key}_change_per_day', "text": "save", "params": {f'{key}_change_per_day': f'@{key}_change_per_day_field'}}    
                res[newButton["name"]]=newButton
        return res
