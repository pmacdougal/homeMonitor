import logging
import json
import time


class Handler:
    NAME = "Handler"

    def __init__(self, topic, metering_queue, messages_per_hour, evaluate_topic):
        self.topic = topic
        self.metering_queue = metering_queue
        self.last_hour = time.localtime().tm_hour
        self.messages_per_hour = messages_per_hour
        self.evaluate_topic = evaluate_topic
        self.message_count = 0
        self.messages_at_last_evaluate = 0
        self.time_of_last_evaluate = time.time()

    def publish(self, topic, message, *, filter=True):
        logging.debug("Handler: %s publish %s to topic %s", self.NAME, message, topic)
        if not filter:
            self.metering_queue.append({"topic": topic, "message": message, "filter": False})
        else:
            self.metering_queue.append({"topic": topic, "message": message})

    def dump_info(self):
        logging.info("%s is handling %s", self.NAME, self.topic)

    def handle_json(self, json_string):        
        logging.debug("%s: got message %s", self.NAME, json_string)
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
        self.publish(self.evaluate_topic, f"{self.NAME} {count}")

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


class Garage(Handler):
    NAME = "Garage"

    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        #print(dir())
        #print(self.__dict__)
        self.publish('g.sq',  data['SQ'])
        self.publish('g.door', data['doorCount'])
        self.publish('g.t0',  data['T0'])
        self.publish('g.t1',  data['T1'])


class Laser(Handler):
    NAME = "Laser"

    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('h.lasercurrent', data['ENERGY']['Current'])


class SoilProbe(Handler):
    NAME = "Soil Probe"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('h.sp', data['S0'])
        self.publish('h.sb', data['S1'])


class Waterer(Handler):
    NAME = "Washer"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('h.r', data['RTCount'])
        self.publish('h.v', data['valveCount'])
        self.publish('h.vr', data['VBATLOAD'])


class Printer(Handler):
    NAME = "Printer"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.150 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.printercurrent', data['ENERGY']['Current'])


class Washer(Handler):
    NAME = "Washer"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.06 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.washercurrent', data['ENERGY']['Current'])
        self.publish('h.washervoltage', data['ENERGY']['Voltage'])


class CatFeeder(Handler):
    NAME = "CatFeeder"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('h.cf', data['CFCount'])


class Ups(Handler):
    NAME = "Ups"
    
    def handle_json(self, message): # not a json string
        super().handle_json(message)
        self.publish('h.ups', str(message, "utf-8"))


class PumpHouse(Handler):
    NAME = "PumpHouse"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('s.it', data['T0'])
        self.publish('s.ot', data['T1'])
        self.publish('s.ht', data['HT'])
        self.publish('s.rt', data['RTCount'])


class LoftTemp(Handler):
    NAME = "LoftTemp"
    
    def handle_json(self, json_string):
        super().handle_json(json_string)
        data = json.loads(json_string)
        self.publish('s.lt', data['T0'], filter=False)