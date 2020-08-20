import logging
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

    def topic(self, topic, handler):
        self.topics.append({"topic":topic, "handler":handler})

    def on_connect(self, client, userdata, flags, result):
        logging.debug("connected with result code %s", result")
        client.subscribe("clock") # so that we get at least one message per minute
        #client.subscribe("ups")
        # [client.subscribe(t["topic"]) for t in self.topics if t.xxx ] # list comprehension
        [client.subscribe(t["topic"]) for t in self.topics] # list comprehension

    def on_message(self, client, userdata, msg):
        logging.debug("got message %s %s at %s", msg.topic, msg.payload, msg.timestamp)
        
        #foo = [t for t in self.topics if t["topic"] == msg.topic]
        #print(f'send {msg.topic} to handler {foo[0].name}')
        #foo[0].handle_json(msg.payload)

        for t in self.topics:
            if t["topic"] == msg.topic:
                print(f'send {msg.topic} to handler {t["handler"].name}')
                t["handler"].handle_json(msg.payload)


    def on_disconnect(self, client, userdata, rc=0):
        logging.debug("Disconnected result code %s", rc)
        # client.loop_stop()

    def start(self):        
        self.client.connect(self.IP_address, self.port) #establish connection
        self.client.loop_start() # spawn thread that calls loop() for us
