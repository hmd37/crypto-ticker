import asyncio

from manager import ConnectionManager

manager = ConnectionManager()
connection_sem = asyncio.Semaphore(100)