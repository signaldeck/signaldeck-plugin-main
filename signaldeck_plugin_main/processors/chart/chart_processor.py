from signaldeck_sdk import DisplayProcessor
from signaldeck_sdk import DisplayData
from .chart_display_data import ChartDisplayData
from datetime import datetime, timedelta
import pandas as pd
from datetime import datetime, timedelta
import logging


CONFIG_OPTION_AGGREGATION="aggregation"
CONFIG_OPTION_AGGREGATION_UNIT="unit"
CONFIG_OPTION_AGGREGATION_TYPE="type"
CONFIG_OPTION_AGGREGATION_N="N"
CONFIG_OPTION_TYPE="type"
DEFAULT_CONFIG_OPTION_TYPE= "scatter"
CONFIG_LASTN_REDUCE="lastNReduce"

class Chart(DisplayProcessor):

    def __init__(self,name,config,valueProvider,collect_data):
        super().__init__(name,config=config,valueProvider=valueProvider,collect_data=collect_data)
        self.valueCache=pd.DataFrame({"date":[],"xValue":[],"yValue":[]}).set_index("date")
        self.logger=logging.getLogger(__name__)

    def getTemplate(self,value):
        return "main/chart.html"
        
    def getAdditionalJsFiles(self,value):
        return [("main","vendor/chartjs/chart-4.5.0-umd-min.js")]
    
    def getAdditionalCssFiles(self,value):
        return [("main","css/chart/style.css")]

    def reduceData(self,data,lastN):
        self.logger.debug(f'lastN={lastN}')
        if data is None:
            return None
        if lastN is not None and not self.config.get(CONFIG_LASTN_REDUCE,False):
            return data[-lastN:]
        step = self.config.get("reduce",{}).get("step",1)
        rolling = self.config.get("reduce",{}).get("rolling",0)
        self.logger.debug(f'reduce={step}')
        self.logger.debug(f'rolling={rolling}')
        if step > 1:
            if rolling > 1:
                data = data.rolling(rolling).mean().dropna()
            data= data[::-1][::step][::-1]
        if lastN is not None:
            data= data[-lastN:]
        return data

    def getIntraDayData(self,offset,onlyOneDay):
        if onlyOneDay:
            return self.hist_value(fullDay=True,days=offset)
        df= self.hist_value(fullDay=True,days=offset+1)    #df is pd.Series!!
        if df is not None:
            df = pd.concat([df,self.hist_value(fullDay=True,days=offset)])
            df = df.sort_index()
        else:
            df=self.hist_value(fullDay=True,days=offset)
        return df.dropna()
  
    def getDiffDayValues(self,date):
        d= self.hist_value(fullDay=True,date=date,days=0,recursive=False)
        xVal=None
        yVal=None
        if d is not None:
            d= d.dropna()
            xVal=d.index[int(len(d)/2)]
            yVal=float(d.iloc[-1])-float(d.iloc[0])
        return xVal, yVal

    def prepareDiffValueForDate(self,unit,N):

        if unit == "day":
            dates=[]
            for i in range(1,N):
                dates.append(datetime.today() + timedelta(days=-i))
            for date in dates:
                if date.date() not in self.valueCache.index:
                    xVal, yVal= self.getDiffDayValues(date)
                    self.logger.info(f'{self.name} Fetched new values for chart: date: {date.date()} , x: {xVal}, y: {yVal}')
                    self.valueCache.loc[date.date()]=pd.Series([xVal,yVal],index=["xValue","yValue"])
                    continue
                break
            self.valueCache= self.valueCache.sort_index()
            if len(self.valueCache) > (N-1):
                self.valueCache= self.valueCache.iloc[-(N-1):]
 

    def getDiffAggData(self, N,unit):
        if unit == "day":
            vals=[]
            dates=[]
            self.prepareDiffValueForDate(unit,N)
            df= self.valueCache.dropna()
            x= list(df["xValue"].values)
            y= list(df["yValue"].values)
            curX, curY = self.getDiffDayValues(datetime.today())
            if curX is not None and curY is not None:
                x.append(curX)
                y.append(curY)
            res= pd.Series(data=y,index=x)
            res.index.name="date"
            return res

    def getDf(self,actionHash,offset=0,lastN=None):
        df=None
        self.logger.debug(f'Fetch data for {actionHash}')
        if self.config.get(CONFIG_OPTION_AGGREGATION,None) is None:
            df= self.getIntraDayData(offset,lastN is None)
        else:
            aggType = self.config[CONFIG_OPTION_AGGREGATION].get(CONFIG_OPTION_AGGREGATION_TYPE,None)
            if aggType == "diff":
                df= self.getDiffAggData(self.config[CONFIG_OPTION_AGGREGATION].get(CONFIG_OPTION_AGGREGATION_N,100),self.config[CONFIG_OPTION_AGGREGATION].get(CONFIG_OPTION_AGGREGATION_UNIT,"day"))    
        if df is not None:
            self.logger.debug(f'Fetched data (len={len(df)}). Now reduce if needed')
        df= self.reduceData(df,lastN)
        if df is not None:
            self.logger.debug(f'ready, len={len(df)}')
        return df

    def getDisplayData(self,value,actionHash,offset=0,lastN=None,currentValues=False) -> DisplayData:
        self.refresh()
        df=None
        if currentValues:
            df=self.hist_value(currentValues=True)
        else:
            df=self.getDf(actionHash,offset=offset,lastN=lastN)
        if df is None:
            return ChartDisplayData(self.ctx, actionHash,self.config.get(CONFIG_OPTION_AGGREGATION,None)) \
                    .withPlotType(self.config.get(CONFIG_OPTION_TYPE,DEFAULT_CONFIG_OPTION_TYPE)).withXValues([]).withYValues([]).withLabel("").withUnit("").withOffset(0).withLastNOption(self.config.get("lastN",None)).withCurrentOption(self.config.get("withCurrent",False))
        yVals=df.values
        dateName = df.index.name
        df = df.reset_index()
        xVals=df[dateName].apply(lambda x : x.timestamp()*1000).values

                

        return ChartDisplayData(self.ctx, actionHash,self.config.get(CONFIG_OPTION_AGGREGATION,None)) \
                .withDate(str(df[dateName].iloc[0].date())) \
                .withXValues(list(xVals)) \
                .withYValues(list(yVals)) \
                .withLabel(self.config.get("title","")) \
                .withUnit(self.config.get("unit","")) \
                .withOffset(offset) \
                .withLastNOption(self.config.get("lastN",None))\
                .withYMinMax(self.config.get("y-range",{}).get("min",None),self.config.get("y-range",{}).get("max",None)) \
                .withPlotType(self.config.get(CONFIG_OPTION_TYPE,DEFAULT_CONFIG_OPTION_TYPE)) \
                .withCurrentOption(self.config.get("withCurrent",False))

    def getAdditionalInfoForClient(self,data:ChartDisplayData):
        return {"render_charts":[data.getDivID()]}
    
    def getBoolParams(self):
        return ["currentValues"]

    def getIntParams(self):
        return ["offset","lastN"]
    
    def getFloatParams(self):
        return []