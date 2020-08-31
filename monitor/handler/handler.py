import logging
import json


class Handler:
    NAME = "Handler"

    def __init__(self, topic, metering_queue):
        self.topic = topic
        self.metering_queue = metering_queue

    def publish(self, topic, message, *, filter=True):
        logging.debug("Handler: %s publish %s to topic %s", self.NAME, message, topic)
        if not filter:
            self.metering_queue.append({"topic": topic, "message": message, "filter": False})
        else:
            self.metering_queue.append({"topic": topic, "message": message})

    def dump_info(self):
        logging.info("%s is handling %s", self.NAME, self.topic)

    def handle_json(self, json_string):
        raise NotImplementedError("You should not directly use a Handler class object")


class Garage(Handler):
    NAME = "Garage"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("Garage: got message %s", json_string)
        data = json.loads(json_string)
        #print(data['doorCount'])
        #print(dir())
        #print(self.__dict__)
        self.publish('g.sq',  data['SQ'])
        self.publish('g.door', data['doorCount'], filter=False)
        self.publish('g.t0',  data['T0'])
        self.publish('g.t1',  data['T1'])


class Laser(Handler):
    NAME = "Laser"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("Laser: got message %s", json_string)
        data = json.loads(json_string)
        #print(data['ENERGY']['Current'])
        self.publish('h.lasercurrent', data['ENERGY']['Current'])


class SoilProbe(Handler):
    NAME = "Soil Probe"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("SoilProbe: got message %s", json_string)
        data = json.loads(json_string)
        self.publish('h.sp', data['S0'])
        self.publish('h.sb', data['S1'])


class Waterer(Handler):
    NAME = "Washer"
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("Waterer: got message %s", json_string)
        data = json.loads(json_string)
        self.publish('h.r', data['RTCount'])
        self.publish('h.v', data['valveCount'])
        self.publish('h.vr', data['VBATLOAD'])


class Printer(Handler):
    NAME = "Printer"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("Printer: got message %s", json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.150 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.printercurrent', data['ENERGY']['Current'])


class Washer(Handler):
    NAME = "Washer"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.debug("Washer: got message %s", json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.06 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.washercurrent', data['ENERGY']['Current'])
        self.publish('h.washervoltage', data['ENERGY']['Voltage'])

class CatFeeder(Handler):
    NAME = "CatFeeder"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, json_string):
        logging.info("CatFeeder: got message %s", json_string)
        data = json.loads(json_string)
        if 'CFCount' in data:
            self.publish('h.cf', data['CFCount'])

class Ups(Handler):
    NAME = "Ups"

    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)

    def handle_json(self, message): # not a json string
        logging.info("Ups: got message %s", message)
        self.publish('h.ups', str(message, "utf-8"))
