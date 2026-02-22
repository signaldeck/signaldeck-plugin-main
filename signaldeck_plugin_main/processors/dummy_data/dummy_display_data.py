from signaldeck_sdk import DisplayData


class DummyDisplayData(DisplayData):

    def withData(self,data):
        self.values= data
        return self

    def getValues(self):
        return self.values
    
    def getValue(self,name):
        return self.values.get(name,None)
    
    def getStateChangeButtonData(self):
        return []
    
    def getExportFields(self):
        return []
    
    def buttons(self):
        res = {}
        for key in self.values.keys():
            newButton = {"name": key, "text": "save", "params": {key: "@"+key+"_field"}}
            res[key] = newButton
        return res
