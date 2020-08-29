import logging
import time
import datetime
from Adafruit_IO import Client


class Adafruit:
    def __init__(self, username, password):
        logging.info("Adafruit: Connecting to io.adafruit.com ...")
        self.aio = Client(username, password)
        self.last_publish_time = 0
        self.feed_cache = {}
        self.last_flush_time = time.time()
        self.period = 2.0 # seconds per message

    def publish(self, topic, message, *, filter=True):
        # Once an hour, empty the feed cache
        now = time.time()
        if 60*60 < now - self.last_flush_time: # The hour has advanced and the minutes have wrapped from 59 to 0
            logging.debug("Adafruit: Clearing feed_cache at %s", datetime.datetime.now())
            self.feed_cache = {}
            self.last_flush_time = now


        delta = now - self.last_publish_time
        if delta < self.period:
            return 1 # return without publishing

        self.last_publish_time = now

        if topic not in self.feed_cache or (filter and message != self.feed_cache[topic]):
            logging.debug("Adafruit: publish %s to %s", message, topic)
            self.feed_cache[topic] = message
            # this next line needs to be un-commented if you want to actually publish to AdaFruit
            #self.aio.send(topic, message)
        else:
            logging.debug("Adafruit: Filtering out %s", topic)

        return 0 # successful processing of this message
