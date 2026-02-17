import asyncio

import logging, datetime,json,time
from signaldeck_sdk import Processor
from flask import render_template
from pathlib import Path
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ConnectionException
from pymodbus.constants import Endian
from signaldeck_sdk import PersistData
from .modbus_pool import ModbusPool


counts = {
    "s32": 2,
    "s16": 1,
    "u32": 2,
    "u16": 1
}

async def getData(client, dataConfigs):
    res={}
    res["date"]=datetime.datetime.now()
    for config in dataConfigs:
        if counts[config.get("type","s16")] == 1:
            res[config.get("name")] = await read_1byte_number(client=client,addr=config.get("address"),unit=1) * config.get("factor",1)
        if counts[config.get("type","s16")] == 2:
            res[config.get("name")] = await read_2bytes_number(client=client,addr=config.get("address"),unit=1) * config.get("factor",1)
    return res


async def read_2bytes_number(client, addr, unit):
    # Lese zwei aufeinanderfolgende Register
    rr = await client.read_holding_registers(addr, count=2, slave=unit)
    if rr.isError():
        raise IOError("Modbus-Fehler beim Lesen")
    # Decode mit pymodbus
    return client.convert_from_registers(
        rr.registers,
        data_type=client.DATATYPE.INT32
    )    

async def read_1byte_number(client: AsyncModbusTcpClient, addr: int, unit: int, byteorder=Endian.BIG) -> int:
    """
    Liest ein einziges 16-Bit-Register und decodiert es als unsigned int.
    Du kannst byteorder auf Little ändern, falls Dein Gerät Little-Endian liefert.
    """
    rr = await client.read_holding_registers(addr, count=1, slave=unit)
    if rr.isError():
        raise IOError(f"Modbus-Fehler beim Lesen von {addr}")
    return client.convert_from_registers(
        rr.registers,
        data_type=client.DATATYPE.UINT16
    )


class modbus(PersistData,Processor):

    def __init__(self,name,config,vP,collect_data):
        super().__init__(name,config,vP,collect_data)
        self.logger = logging.getLogger(__name__)
        self.is_running=True
        self.client = None

    def shutdown(self):
        asyncio.run(ModbusPool.close(self.logger))
        

    def get_asyncio_tasks(self,collect_data):
        """
        Liefert die Liste von Async-Tasks für den Manager.
        """
        if collect_data:
            return [self.get_data_from_modbus()]
        return []

    async def get_data_from_modbus(self):
        """
        Periodisches Polling
        """
        self.logger.info(f"Start modbus logger: running={self.is_running}")
        interval = float(self.config.get("read_interval", 1.0))
        while self.is_running:
            try:
                starttime = datetime.datetime.now().timestamp()
                await self._ensure_client()
                self.logger.debug(f"Modbus client: {self.client}")
                data = await getData(self.client, self.config.get("data", []))
                self.logger.debug(f"New data: {data}")
                self.save_data(data)
            except Exception as e:
                self.logger.error("Error while processing data..", exc_info=True)
            # Sleep interval
            
            self.logger.debug(f"Next poll in {interval} seconds")
            neededTime = datetime.datetime.now().timestamp() - starttime
            if neededTime < interval:
                await asyncio.sleep(interval-neededTime)

    async def _ensure_client(self):
        ip   = self.config["ip"]
        port = int(self.config.get("port", 502))
        timeout = self.config.get("timeout", 3)
        self.client = await ModbusPool.get_client(ip, port, timeout)

    