import logging
import json


class Handler:
    def __init__(self, topic, metering_queue):
        self.name = "Handler"
        self.topic = topic
        self.metering_queue = metering_queue

    def publish(self, topic, message):
        logging.info("Publish %s to topic %s", message, topic)
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
        logging.debug("got message %s", json_string)
        data = json.loads(json_string)
        #print(data['doorCount'])
        #print(self.__dict__)
        self.publish('g.sq',  data['SQ'])
        self.publish('g.door', data['doorCount'])
        self.publish('g.t0',  data['T0'])
        self.publish('g.t1',  data['T1'])


class Laser(Handler):
    def __init__(self, topic, metering_queue):
        Handler.__init__(self, topic, metering_queue)
        self.name = "Laser"

    def handle_json(self, json_string):
        logging.debug("got message %s", json_string)
        data = json.loads(json_string)
        #print(data['ENERGY']['Current'])
        self.publish('h.lasercurrent', data['ENERGY']['Current'])

