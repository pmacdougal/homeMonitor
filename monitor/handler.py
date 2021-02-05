import logging
import json
import time


class Handler:
    NAME = 'Handler'

    def __init__(self, topic, metering_queue, messages_per_hour, evaluate_topic):
        self.topic = topic
        self.metering_queue = metering_queue
        self.last_hour = time.localtime().tm_hour
        self.messages_per_hour = messages_per_hour
        self.evaluate_topic = evaluate_topic
        self.message_count = 0
        self.messages_at_last_evaluate = 0
        self.time_of_last_evaluate = time.time()
        self.list_of_keys = []

    def setup(self, topic, key, *, clamp=0, filter=True):
        self.list_of_keys.append({'key': key, 'topic': topic, 'clamp': clamp, 'filter': filter})

    def publish(self, topic, message, *, filter=True):
        logging.debug('Handler: %s publish %s to topic %s', self.NAME, message, topic)
        if not filter:
            self.metering_queue.append({'topic': topic, 'message': message, 'filter': False})
        else:
            self.metering_queue.append({'topic': topic, 'message': message})

    def dump_info(self):
        logging.info('%s is handling %s', self.NAME, self.topic)

    def handle_json(self, json_string):
        logging.debug('%s: got message %s', self.NAME, json_string)
        self.message_count += 1

    def evaluate(self):
        count = self.message_count - self.messages_at_last_evaluate
        delta = time.time() - self.time_of_last_evaluate
        self.messages_at_last_evaluate = self.message_count
        self.time_of_last_evaluate = time.time()
        # we have seen {count} messages in {delta} seconds
        # if that is typical, how many would we see in an hour?
        hourly_rate = 60*60*count // delta

        # for now
        self.publish(self.evaluate_topic, f'{self.NAME} {count}')

        if 0 == self.messages_per_hour: # e.g. Ups
            if 0 < hourly_rate:
                pass # unexpected
        elif 1 == self.messages_per_hour: # e.g. SoilProbe
            if 0 == hourly_rate:
                pass # less than unexpected, but often encountered
            elif 1 < hourly_rate:
                pass # more than unexpected, but often encountered
            else:
                pass # normal range
        else:
            if 0.90*self.messages_per_hour > hourly_rate:
                pass # less than unexpected
            elif 1.10*self.messages_per_hour < hourly_rate:
                pass # more than unexpected
            else:
                pass # normal range

class Generic(Handler):
    NAME = 'Generic'

    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        for k in self.list_of_keys:
            self.publish(k['topic'], data[k['key']], filter=k['filter'])


class GenericEnergy(Handler):
    NAME = 'Generic'

    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        for k in self.list_of_keys:
            if k['clamp'] > data['ENERGY'][k['key']]:
                data['ENERGY'][k['key']] = 0.0
            self.publish(k['topic'], data['ENERGY'][k['key']], filter=k['filter'])

class GenericString(Handler):
    NAME = 'Generic'

    def handle_json(self, message):
        super().handle_json(message)
        for k in self.list_of_keys:
            self.publish(k['topic'], str(message, 'utf-8'), filter=k['filter'])

