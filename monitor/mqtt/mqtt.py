import logging
import json
import paho.mqtt.client as mqtt

class MqttMonitor:
    def __init__(self, IP_address, *, port=1883):
        self.IP_address = IP_address
        self.port = port
        self.client = mqtt.Client("")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.topics = []

    def topic(self, handler):
        self.topics.append({"topic":handler.topic, "handler":handler})

    def on_connect(self, client, userdata, flags, result):
        logging.debug("MqttMonitor: connected with result code %s", result)
        client.subscribe("clock") # so that we get at least one message per minute
        #client.subscribe("ups")
        # [client.subscribe(t["topic"]) for t in self.topics if t.xxx ] # list comprehension
        [client.subscribe(t["topic"]) for t in self.topics] # list comprehension of all topics
        # do we want to publish any status message to adafruit?

    def on_message(self, client, userdata, msg):
        logging.debug("MqttMonitor: got message %s %s at %s", msg.topic, msg.payload, msg.timestamp)
        
        #foo = [t for t in self.topics if t["topic"] == msg.topic]
        #print(f'MqttMonitor: send {msg.topic} to handler {foo[0].name}')
        #foo[0].handle_json(msg.payload)

        # Send the message payload to the proper handler
        for t in self.topics:
            if t["topic"] == msg.topic:
                #print(f'MqttMonitor: send {msg.topic} to handler {t["handler"].name}')
                try:
                    t["handler"].handle_json(msg.payload)
                except JSONDecodeError:
                    pass
                break # break out of the loop early


    def on_disconnect(self, client, userdata, rc=0):
        logging.debug("MqttMonitor: Disconnected result code %s", rc)
        # client.loop_stop()

    def start(self):        
        self.client.connect(self.IP_address, self.port) #establish connection
        self.client.loop_start() # spawn thread that calls loop() for us
