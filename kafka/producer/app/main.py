import json
import logging
import websockets
from kafka import KafkaProducer
from apscheduler.schedulers.blocking import BlockingScheduler
from config import Config
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')

class Worker:
    def __init__(self):
        self.binance_websockets = Config.binance_websockets
        self.bootstrap_server = Config.bootstrap_server
        self.topic = Config.topic
        self.producer = None  # Initialize producer

    async def config_producer(self):
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_server,
            value_serializer=lambda m: json.dumps(m).encode('utf-8'),
            retries=3
        )
        return producer

    async def on_message(self, message):
        try:
            data = json.loads(message)
            print(f"Received data from Binance: {data}")

            await self.send_producer_data(self.producer, data)
        except Exception as e:
            logging.error(f"Error processing message: {e}")

    async def on_error(self, error):
        logging.error(f"Error with websocket connection: {error}")

    async def on_close(self):
        logging.info("Websocket connection closed")

    async def on_open(self):
        logging.info("Websocket connection opened")

    async def start_websocket(self, nifi_host, nifi_port):
        self.producer = await self.config_producer()  # Await the producer configuration
        async with websockets.connect(self.binance_websockets) as ws_binance:
            while True:
                try:
                    message = await ws_binance.recv()
                    await self.on_message(message)
                    
                except websockets.exceptions.ConnectionClosedError as e:
                    await self.on_close(str(e))
                    break

                except Exception as e:
                    await self.on_error(str(e))

    async def send_producer_data(self, producer, data):
        producer.send(self.topic, data)
        logging.info("Successfully sent message!")

    async def run_worker(self, nifi_host, nifi_port):
        try:
            await self.start_websocket(nifi_host, nifi_port)  # Await starting the websocket
        except Exception as e:
            logging.error(f"Error running worker: {e}")


if __name__ == '__main__':
    nifi_host = "nifi"
    nifi_port = 6993

    worker = Worker()
    asyncio.run(worker.run_worker(nifi_host, nifi_port))  # Ensure to use asyncio.run to execute the coroutine
