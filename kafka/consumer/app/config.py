import os

class Config(object):

  bootstrap_server = os.environ['BOOTSTRAP_SERVER']
  topic = os.environ['TOPIC']
  producer_topic = os.environ['PRODUCER_TOPIC']