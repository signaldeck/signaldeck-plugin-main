from signaldeck_sdk import DisplayData


class DummyDisplayData(DisplayData):
    def __init__(self,hash,params):
        super().__init__(hash)
        self.currParams=params

    def getValues(self):
        return self.currParams
    
    def getValue(self,name):
        return self.currParams.get(name,None)
    
    def getStateChangeButtonData(self):
        return []
    
    def getExportFields(self):
        return []