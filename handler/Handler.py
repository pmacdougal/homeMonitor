import logging
import json


class Handler:
    def __init__(self, topic, metering_queue):
        self.name = "Handler"
        self.topic = topic
        self.metering_queue = metering_queue

    def publish(self, topic, message, *, filter=True):
        logging.info("Handler: %s publish %s to topic %s", self.name, message, topic)
        if not filter:
            self.metering_queue.append({"topic": topic, "message": message, "filter": False})
        else:
            self.metering_queue.append({"topic": topic, "message": message})

    def dump_info(self):
        logging.info("%s is handling %s", self.name, self.topic)

    def handle_json(self, json_string):
        raise NotImplementedError("You should not directly use a Handler class object")


class Garage(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Garage"

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
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Laser"

    def handle_json(self, json_string):
        logging.debug("Laser: got message %s", json_string)
        data = json.loads(json_string)
        #print(data['ENERGY']['Current'])
        self.publish('h.lasercurrent', data['ENERGY']['Current'])


class SoilProbe(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Soil Probe"

    def handle_json(self, json_string):
        logging.debug("SoilProbe: got message %s", json_string)
        data = json.loads(json_string)
        self.publish('h.sp', data['S0'])
        self.publish('h.sbp', data['S1'])


class Waterer(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Waterer"

    def handle_json(self, json_string):
        logging.debug("Waterer: got message %s", json_string)
        data = json.loads(json_string)
        self.publish('h.r', data['RTCount'])
        self.publish('h.v', data['valveCount'])
        self.publish('h.vR', data['VBATLOAD'])


class Printer(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Printer"

    def handle_json(self, json_string):
        logging.debug("Printer: got message %s", json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.150 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.printercurrent', data['ENERGY']['Current'])


class Washer(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Washer"

    def handle_json(self, json_string):
        logging.debug("Washer: got message %s", json_string)
        data = json.loads(json_string)
        # small current while idle is not interesting, so clamp
        if (0.06 > data['ENERGY']['Current']):
            data['ENERGY']['Current'] = 0.0
        self.publish('h.washercurrent', data['ENERGY']['Current'])
        self.publish('h.washervoltage', data['ENERGY']['Voltage'])

