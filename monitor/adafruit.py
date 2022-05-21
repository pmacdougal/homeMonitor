import logging
import time
import datetime
from Adafruit_IO import Client, MQTTClient, RequestError, ThrottlingError, AdafruitIOError, Data
from urllib3.exceptions import MaxRetryError, NewConnectionError
#from .gprs import Gprs
from .bg96 import Bg96

'''
ToDo:
'''
class Adafruit:
    # message states
    INITIAL = 1
    INFLIGHT = 2
    PUBLISHED = 3
    ERROR = 4

    def __init__(self, username, password, access):
        logging.info('Adafruit.__init__(): Connecting to io.adafruit.com ...')
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
                logging.info('Adafruit.__init__(): Connection timed out')
            else:
                self.aio.loop_background()
        elif 'lte' == self.access:
            self.gprs = Bg96('/dev/ttyS0')
        else:
            logging.error('Adafruit.__init__(): access method %s is not defined', self.access)
            raise NotImplementedError

    def mqtt_connected(self, client):
        logging.info('Adafruit.mqtt_connected(): io.adafruit.com MQTT broker connected.')
        client.subscribe('pmacdougal/throttle') # feed from AdaFruit to subscribe to
        #client.subscribe('pmacdougal/feeds/g.sq') # feed from AdaFruit to subscribe to for testing
        #client.subscribe('pmacdougal/feeds/s.mps') # feed from AdaFruit

    def mqtt_disconnected(self, client):
        logging.info('Adafruit.mqtt_disconnected(): io.adafruit.com MQTT broker disconnected.')

    def mqtt_message(self, client, topic, payload):
        logging.info('Adafruit.mqtt_message(): got message %s with value %s.', topic, payload)
        if 'pmacdougal/feeds/s.mps' == topic:
            pass
            #self.local_broker.publish(topic, payload) # forward to local broker



    def loop(self):
        if 'rest' == self.access:
            time.sleep(1)
        elif 'mqtt' == self.access:
            time.sleep(1)
        elif 'lte' == self.access:
            # let radio process serial data
            self.gprs.loop()
        else:
            logging.error('Adafruit.loop(): access method %s is not defined', self.access)
            raise NotImplementedError

    def publish(self, topic, message, state, filter):
        # Once an hour, empty the feed cache
        localtime = time.localtime()
        if localtime.tm_hour != self.last_hour:
            logging.info('Adafruit.publish(): Clearing feed_cache at %s', datetime.datetime.now())
            self.feed_cache = {}
            self.publishes_this_hour = 0
            self.last_hour = localtime.tm_hour
            logging.setLevel(self.gprs.savedLevel) # restore logging verbosity at the top of the hour
        self.publishes_this_hour += 1

        if Adafruit.INFLIGHT == state:
            if 'lte' == self.access:
                if self.gprs.successfully_published:
                    self.gprs.successfully_published = False
                    logging.debug('Adafruit: publish: GPRS indicates message %s was sent to Adafruit', topic)
                    return Adafruit.PUBLISHED

                if self.gprs.radio_error:
                    self.gprs.radio_error = False
                    logging.error('Adafruit: publish: GPRS indicates radio error for message %s', topic)
                    return Adafruit.ERROR

                # allow radio to process serial data
                self.gprs.loop()
                return Adafruit.INFLIGHT
            else:
                logging.error('Adafruit: publish() called with state INFLIGHT, but access is %s', self.access)
                return Adafruit.ERROR
            # I don't think we can get here
            return Adafruit.ERROR
        elif Adafruit.ERROR == state:
            # this is weird
            logging.error('Adafruit: publish() called with state ERROR')
            return Adafruit.ERROR
        elif Adafruit.PUBLISHED == state:
            # why did we get called?
            return Adafruit.PUBLISHED
        elif Adafruit.INITIAL == state:
            if (topic not in self.feed_cache) or (not filter) or message != self.feed_cache[topic]:
                # rate limiting
                delta = time.time() - self.last_publish_time
                if delta < self.period:
                    time.sleep(self.period - delta)

                try:
                    if True: # set False for testing without sending to AdaFruit
                        if 'rest' == self.access:
                            self.last_publish_time = time.time()
                            #logging.info('Adafruit.publish(): Adding %s to feed_cache', topic)
                            self.feed_cache[topic] = message
                            logging.info('Adafruit.publish(): publish %s to %s', message, topic)
                            pub_result = self.aio.send_data(topic, message)
                            # Data(created_epoch=1598796144, created_at='2020-08-30T14:02:24Z', updated_at=None, value='122', completed_at=None, feed_id=1404586, expiration='2020-10-29T14:02:24Z', position=None, id='0EH9YC6HB3M2YETZXNJS79D0HV', lat=None, lon=None, ele=None)
                            # I don't know what a failure result looks like
                            return Adafruit.PUBLISHED # successful handing of message

                        elif 'mqtt' == self.access:
                            if self.aio.is_connected():
                                self.last_publish_time = time.time()
                                logging.info('Adafruit.publish(): Adding %s to feed_cache', topic)
                                self.feed_cache[topic] = message
                                logging.debug('Adafruit.publish(): publish %s to %s', message, topic)
                                self.aio.publish(topic, message)
                                return Adafruit.PUBLISHED # successful handling of message
                            else:
                                logging.error('Adafruit.publish():: Not connected error')
                                try:
                                    self.aio.connect()
                                except TimeoutError:
                                    logging.info('Adafruit.publish(): Connection timed out')
                                return Adafruit.ERROR

                        elif 'lte' == self.access:
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
                                logging.debug('Adafruit.publish(): Adding %s to feed_cache', topic)
                                self.feed_cache[topic] = message
                                logging.debug('Adafruit.publish(): publish %s to %s', message, topic)
                                self.gprs.publish(topic, message)
                                # getting here does not mean that the data got to AdaFruit
                                return Adafruit.INFLIGHT # we have queued the publish, but must wait for self.gprs.successfully_published to go True
                            else:
                                # wait for radio
                                return state
                        else:
                            logging.error('Adafruit.publish(): access method %s is not defined', self.access)
                            raise NotImplementedError

                except RequestError:
                    logging.error('Adafruit.publish(): Exception: Got a RequestError for %s', topic, exc_info=True)
                except ThrottlingError:
                    logging.error('Adafruit.publish(): Exception: Got a ThrottlingError for %s', topic, exc_info=True)
                except AdafruitIOError:
                    logging.error('Adafruit.publish(): Exception: Got an AdafruitIOError for %s', topic, exc_info=True)
                except NewConnectionError as e:
                    logging.error('Adafruit.publish(): New connection exception: %s', e, exc_info=False)
                except MaxRetryError as e:
                    logging.error('Adafruit.publish(): Retry exception: %s', e, exc_info=False)
                except ConnectionError as e:
                    logging.error('Adafruit.publish(): Connection exception: %s', e, exc_info=False)
                except Exception as e:
                    logging.error('Adafruit.publish(): Exception: %s', e, exc_info=True)
                else:
                    # I don't think we can get here
                    logging.error('Adafruit.publish(): Try block else clause executed')

            else:
                logging.debug('Adafruit.publish(): Filtering out %s %s %d %d %d', topic, message, (not topic in self.feed_cache), (filter), (topic in self.feed_cache and message != self.feed_cache[topic]))
                return Adafruit.PUBLISHED # successful processing of this message

            return Adafruit.ERROR
        else:
            logging.error('Adafruit.publish(): write code for state %d', state)
            return Adafruit.ERROR

        # I don't think we can get here
        return Adafruit.ERROR
    
