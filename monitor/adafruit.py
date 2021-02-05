import logging
import time
import datetime
from Adafruit_IO import Client, MQTTClient, RequestError, ThrottlingError, AdafruitIOError, Data
from .gprs import Gprs
from .bg96 import Bg96

'''
ToDo:
    figure out how to tell that the GPRS radio got SEND OK on publish
'''
class Adafruit:
    def __init__(self, username, password, access):
        logging.info('Adafruit: Connecting to io.adafruit.com ...')
        self.access = access
        self.last_publish_time = 0
        self.feed_cache = {}
        self.last_hour = time.localtime().tm_hour
        self.publishes_this_hour = 0
        self.period = 2.0 # seconds per message
        if 'rest' == self.access:
            self.aio = Client(username, password)
        elif 'mqtt' == self.access:
            self.aio = MQTTClient(username, password, secure=False)
            self.aio.on_connect    = self.mqtt_connected
            self.aio.on_disconnect = self.mqtt_disconnected
            self.aio.on_message    = self.mqtt_message
            try:
                self.aio.connect()
            except TimeoutError:
                logging.info('Adafruit: Connection timed out')
            else:
                self.aio.loop_background()
        elif 'lte' == self.access:
            self.gprs = Bg96('/dev/ttyS0')
        elif 'gprs' == self.access:
            self.gprs = Gprs('/dev/ttyS0')
        else:
            logging.error('access method %s is not defined', self.access)
            raise NotImplementedError

    def mqtt_connected(self, client):
        logging.info('Adafruit.mqtt_connected(): io.adafruit.com MQTT broker connected.')
        client.subscribe('pmacdougal/throttle') # feed from AdaFruit to subscribe to
        client.subscribe('pmacdougal/feeds/g.sq') # feed from AdaFruit to subscribe to for testing

    def mqtt_disconnected(self, client):
        logging.info('Adafruit.mqtt_disconnected(): io.adafruit.com MQTT broker disconnected.')

    def mqtt_message(self, client, topic, payload):
        logging.info('Adafruit.mqtt_message(): got message %s with value %s.', topic, payload)

    def loop(self):
        if 'rest' == self.access:
            time.sleep(1)
        elif 'mqtt' == self.access:
            time.sleep(1)
        elif 'lte' == self.access:
            # let radio process serial data
            self.gprs.loop()
        elif 'gprs' == self.access:
            # let radio process serial data
            self.gprs.loop()
        else:
            logging.error('access method %s is not defined', self.access)
            raise NotImplementedError

    def publish(self, topic, message, *, filter=True):
        # Once an hour, empty the feed cache
        localtime = time.localtime()
        if localtime.tm_hour != self.last_hour:
            logging.info('Adafruit: Clearing feed_cache at %s', datetime.datetime.now())
            self.feed_cache = {}
            self.publishes_this_hour = 0
            self.last_hour = localtime.tm_hour
        self.publishes_this_hour += 1

        if (topic not in self.feed_cache) or (not filter) or message != self.feed_cache[topic]:
            # rate limiting
            delta = time.time() - self.last_publish_time
            if delta < self.period:
                time.sleep(self.period - delta)

            try:
                when = datetime.datetime.now()
                if True: # set False for testing without sending to AdaFruit
                    if 'rest' == self.access:
                        self.last_publish_time = time.time()
                        logging.info('Adafruit.publish(): Adding %s to feed_cache', topic)
                        self.feed_cache[topic] = message
                        logging.debug('Adafruit: publish %s to %s', message, topic)
                        pub_result = self.aio.send_data(topic, message)
                        # Data(created_epoch=1598796144, created_at='2020-08-30T14:02:24Z', updated_at=None, value='122', completed_at=None, feed_id=1404586, expiration='2020-10-29T14:02:24Z', position=None, id='0EH9YC6HB3M2YETZXNJS79D0HV', lat=None, lon=None, ele=None)
                        when = pub_result.created_at
                        return 0 # successful handing of message
                    elif 'mqtt' == self.access:
                        if self.aio.is_connected():
                            self.last_publish_time = time.time()
                            logging.info('Adafruit.publish(): Adding %s to feed_cache', topic)
                            self.feed_cache[topic] = message
                            logging.debug('Adafruit: publish %s to %s', message, topic)
                            self.aio.publish(topic, message)
                            return 0 # successful handling of message
                        else:
                            logging.error('Adafruit: publish: Not connected error')
                            return 1 # unsuccessful processing of this message
                    elif 'lte' == self.access or 'gprs' == self.access:
                        # allow radio to process serial data
                        self.gprs.loop()
                        # see if radio is ready for data
                        if self.gprs.is_ready():
                            #if self.gprs.successfully_published:
                            #    # message was published (we got +QMTPUB)
                            #    self.gprs.successfully_published = False
                            #    logging.info('Adafruit: publish: GPRS indicates message %s was sent to Adafruit', self.gprs.lasttopic)
                            #    return 0 # casues message to be popped
                            self.last_publish_time = time.time()
                            logging.info('Adafruit.publish(): Adding %s to feed_cache', topic)
                            self.feed_cache[topic] = message
                            logging.debug('Adafruit: publish %s to %s', message, topic)
                            self.gprs.publish(topic, message)
                            # getting here does not mean that the data got to AdaFruit
                            return 1 # we have queued the publish, but must wait for self.gprs.successfully_published to go True
                        else:
                            return 1 # unsuccessful processing of this message
                    else:
                        logging.error('access method %s is not defined', self.access)
                        raise NotImplementedError

            except RequestError:
                logging.error('Exception: Got a RequestError for %s', topic, exc_info=True)
            except ThrottlingError:
                logging.error('Exception: Got a ThrottlingError for %s', topic, exc_info=True)
            except AdafruitIOError:
                logging.error('Exception: Got an AdafruitIOError for %s', topic, exc_info=True)
            except Exception as e:
                logging.error('Exception: %s', e, exc_info=True)
            else:
                logging.info('Adafruit: Publish succeeded for %s %s at %s', topic, message, when)

        else:
            logging.debug('Adafruit: Filtering out %s %s %d %d %d', topic, message, (not topic in self.feed_cache), (filter), (topic in self.feed_cache and message != self.feed_cache[topic]))
            return 0 # successful processing of this message

        return 1
