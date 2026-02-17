# modules/modbus_pool.py
import asyncio
from pymodbus.client import AsyncModbusTcpClient

class ModbusPool:
    _clients: dict[str, AsyncModbusTcpClient] = {}
    _locks:   dict[str, asyncio.Lock]             = {}
    _last_attempt: dict[str, float]               = {}
    

    @classmethod
    async def close(cls,logger):
        for key, client in list(cls._clients.items()):
            ip, port = key.split(":")
            await cls.shutdown_client(ip, int(port),logger)
        cls._clients={}

    @classmethod
    async def shutdown_client(cls, ip: str, port: int, logger):
        key = f"{ip}:{port}"
        logger.info(f'Close modbus client: {key}')
        client = cls._clients.pop(key, None)
        cls._locks.pop(key, None)
        cls._last_attempt.pop(key, None)
        if client:
            try:
                result = client.close()  # kann coroutine oder None sein
                if asyncio.iscoroutine(result):
                    await result
                if logger:
                    logger.info(f"Closed Modbus client: {ip}:{port}")
            except Exception as e:
                if logger:
                    logger.warning(f"Error closing Modbus client {ip}:{port}: {e}")

    @classmethod
    async def get_client(cls, ip: str, port: int, timeout: float):
        key = f"{ip}:{port}"
        # pro key genau einen Lock
        lock = cls._locks.setdefault(key, asyncio.Lock())

        async with lock:
            # Client-Instanz ggf. anlegen
            client = cls._clients.get(key)
            if client is None:
                client = AsyncModbusTcpClient(host=ip, 
                port=port, 
                timeout=timeout,
                retries=0)
                cls._clients[key] = client
                # initial so, dass beim ersten Mal sofort verbunden wird
                cls._last_attempt[key] = 0.0

            # nur, wenn noch nicht verbunden, drosselt Connect-Versuche
            if not getattr(client, "connected", False):
                loop = asyncio.get_running_loop()
                now = loop.time()
                last = cls._last_attempt.get(key, 0.0)

                # nur max. 1 Versuch pro Sekunde
                if now - last >= 1.0:
                    await client.connect()
                    cls._last_attempt[key] = now
                # else: warten, kein neuer Connect-Versuch

            return client
