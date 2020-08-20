import logging
from Adafruit_IO import Client

class Adafruit:
    def __init__(self, usename, password):
        self.username = username
        self.password = password
        self.feed_dict = {}
        logging.info("Adafruit: Connecting to io.adafruit.com ...")
        self.aio = Client(self.username, self.password)


    def publish(self, topic, message):
        if topic not in feedDict or message != feedDict[topic]:
            logging.debug("Adafruit: publish %s to %s", message, topic)
            feedDict[topic] = message
            self.aio.send(topic, message)
        else:
            logging.debug(("Adafruit: Filtering out %s", topic)
            




