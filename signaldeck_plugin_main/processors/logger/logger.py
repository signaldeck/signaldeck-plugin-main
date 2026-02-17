import json
import os
import time
import logging
from signaldeck_sdk import Processor

class logger(Processor):

    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.logger = logging.getLogger(__name__)

    def process(self,value,actionHash,file=None):
        self.logger.info(f'Start processing {value}')
        self.logger.info(value)
        time.sleep(10)
        self.logger.info(f'Finished processing {value}')