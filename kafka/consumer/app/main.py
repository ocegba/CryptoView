from apscheduler.schedulers.blocking import BlockingScheduler
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
import logging
from config import Config
import json
from time import sleep
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, LongType, BooleanType, DoubleType
from pyspark.sql.functions import col, expr, from_json, from_unixtime, to_timestamp, date_format


logging.basicConfig(level=logging.INFO, format='%(asctime)s :: %(levelname)s :: %(message)s')
logger = logging.getLogger(__name__)

class Worker:
    def __init__(self):
        logger.info("Initializing Worker")
        self.bootstrap_server = Config.bootstrap_server
        self.producer_topic = Config.producer_topic
        self.topic = Config.topic
        self.spark = SparkSession.builder.master("spark://spark-master:7077").appName("KafkaToSpark").getOrCreate()

    def config_consumer(self):
        logger.info("Configuring Kafka consumer")
        consumer = KafkaConsumer(
            self.topic,
            group_id='nifi_binance_overview_consumer',
            bootstrap_servers=self.bootstrap_server,
            auto_offset_reset='latest',
        )
        return consumer

    def config_producer(self):
        logger.info("Configuring Kafka producer")
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_server,
            value_serializer=lambda m: json.dumps(m).encode('utf-8'),
            retries=3
        )
        return producer

    def send_producer_data(self, producer, data):
        try:
            logger.info(f"Sending data: {data}")
            future = producer.send(self.producer_topic, data)
            result = future.get(timeout=60)
            logger.info(f"Successfully sent message to {result.topic}:{result.partition}")
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")

    def run_tasks(self):
        try:
            consumer = self.config_consumer()
            producer = self.config_producer()
            for data in consumer:
                json_data = data.value.decode('utf-8')
                processor = BinanceDataProcessor()
                parsed_df = processor.process_json_data(json_data, 18800000)
                parsed_df.show()
                data_dicts = [row.asDict() for row in parsed_df.collect()]
                self.send_producer_data(producer, data_dicts[0])

        except KafkaError as err:
            logger.error(f"Kafka error: {err}")
        except Exception as err:
            logger.error(f"Exception in run_tasks: {err}")

    def run_worker(self):
        logger.info("Running worker")
        self.run_tasks()

class BinanceDataProcessor:
    def __init__(self):
        logger.info("Initializing BinanceDataProcessor")
        self.spark = SparkSession.builder.appName("BinanceDataProcessing").getOrCreate()
        self.spark.sql('set spark.sql.caseSensitive=true')
        
        self.binance_schema = StructType([
            StructField("e", StringType()),
            StructField("E", LongType()),
            StructField("s", StringType()),
            StructField("k", StructType([
                StructField("t", LongType()), 
                StructField("T", LongType()), 
                StructField("s", StringType()), 
                StructField("i", StringType()), 
                StructField("f", LongType()), 
                StructField("L", LongType()), 
                StructField("o", StringType()), 
                StructField("c", StringType()), 
                StructField("h", StringType()), 
                StructField("l", StringType()), 
                StructField("v", StringType()), 
                StructField("n", LongType()), 
                StructField("x", BooleanType()), 
                StructField("q", StringType()), 
                StructField("V", StringType()), 
                StructField("Q", StringType()), 
                StructField("B", StringType())
            ]))
        ])

    def process_json_data(self, json_data, circulating_supply):
        logger.info("Processing JSON data")
        df = self.spark.createDataFrame([(json_data,)], ["value"])
        parsed_df = (
            df.withColumn("json_data", from_json(col("value"), self.binance_schema))
            .select(
                col("json_data.e").alias("event_type"),
                to_timestamp(from_unixtime(col("json_data.E") / 1000)).alias("event_time"),
                col("json_data.s").alias("symbol"),
                to_timestamp(from_unixtime(col("json_data.k.t") / 1000)).alias("start_time"),
                to_timestamp(from_unixtime(col("json_data.k.T") / 1000)).alias("end_time"),
                col("json_data.k.s").alias("kline_symbol"),
                col("json_data.k.i").alias("interval"),
                col("json_data.k.f").alias("first_trade_id"),
                col("json_data.k.L").alias("last_trade_id"),
                expr("round(json_data.k.o, 3)").alias("open_price"),
                expr("round(json_data.k.c, 3)").alias("close_price"),
                expr("round(json_data.k.h, 3)").alias("high_price"),
                expr("round(json_data.k.l, 3)").alias("low_price"),
                expr("round(json_data.k.v, 3)").alias("volume"),
                expr("round(json_data.k.n, 3)").alias("number_of_trades"),
                col("json_data.k.x").alias("is_kline_closed"),
                expr("round(json_data.k.q, 3)").alias("quote_asset_volume"),
                expr("round(json_data.k.V, 3)").alias("active_buy_volume"),
                expr("round(json_data.k.Q, 3)").alias("active_buy_quote_volume"),
                expr("round(json_data.k.B, 3)").alias("ignore"),
                expr("round((json_data.k.h - json_data.k.l) / 2, 3)").alias("bid_ask_spread"),
                expr("round(json_data.k.v / (json_data.k.h - json_data.k.l), 3)").alias("liquidity_ratio"),
                expr("round((close_price - open_price) / close_price, 3)").alias("profit_margin"),
                expr("round(((close_price - open_price) / open_price) * 100, 3)").alias("roi"),
                expr("round(((high_price - low_price) / open_price) * 100, 3)").alias("price_spread_percentage")
            )
            .withColumn("close_price", col("close_price").cast(DoubleType()))
            .withColumn("volume", col("volume").cast(DoubleType()))
            .withColumn("market_cap", expr("round(close_price * {}, 3)".format(circulating_supply)))
            .withColumn("nvtratio", expr("round(volume / {}, 3)".format(circulating_supply)))
            .withColumn("price_change", expr("round(close_price - open_price, 3)"))
            .withColumn("high_low_range", expr("round(high_price - low_price, 3)"))
            .withColumn("average_price", expr("round((open_price + close_price + high_price + low_price) / 4, 3)"))
            .withColumn("price_spread", expr("round(high_price - low_price, 3)"))
            .withColumn("price_range", expr("round(close_price - open_price, 3)"))
            .withColumn("trade_liquidity", expr("round(volume / (close_price - open_price), 3)"))
            .drop("json_data")
            .drop("value")
        )
        logger.info("Completed processing JSON data")
        
        datetime_cols = ['event_time', 'start_time', 'end_time']
        for col_name in datetime_cols:
            parsed_df = parsed_df.withColumn(col_name, date_format(col(col_name), "yyyy-MM-dd'T'HH:mm:ss'Z'").cast(StringType()))

        return parsed_df

    def stop(self):
        logger.info("Stopping Spark session")
        self.spark.stop()

if __name__ == "__main__":
    worker = Worker()
    worker.run_worker()