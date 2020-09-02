#!/usr/bin/env python3
# This script monitors topics in my local MQTT broker
# Some messages are forwarded to io.adafruit.com
# HTML files for the status of devices are created
import logging
import time
import sys
from monitor.mqtt.mqtt import MqttMonitor
from monitor.handler.handler import Garage, Laser, SoilProbe, Waterer, Printer, Washer, CatFeeder, Ups
from monitor.adafruit.adafruit import Adafruit
from monitor.private import password
# private.py is not part of the checked in code.  You will need to create it.
# It is a one line file with your Adafruit IO access key in it:
#     password = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

class Monitor:
    def __init__(self):
        pass

    def run(self, msg):
        logging.basicConfig(level=logging.INFO)
        # configure device handlers
        metering_queue = []
        metering_queue.append({"topic": "h.mqtt", "message": msg})
        aio = Adafruit('pmacdougal', password)

        try:
            # create an MQTT monitor and set up the topics being monitored
            monitor = MqttMonitor("192.168.2.30")
            monitor.topic(Garage("tele/99e934/SENSOR", metering_queue, 240)
            monitor.topic(SoilProbe('tele/3154ff/SENSOR', metering_queue, 1))
            monitor.topic(Waterer('tele/99e813/SENSOR', metering_queue, 240)
            monitor.topic(CatFeeder('tele/9215de/SENSOR', metering_queue, 240)
            monitor.topic(Printer('tele/sonoffD/SENSOR', metering_queue, 240)
            monitor.topic(Washer('tele/sonoffE/SENSOR', metering_queue, 240)
            monitor.topic(Laser("tele/sonoffP/SENSOR", metering_queue, 240)
            monitor.topic(Ups("ups", metering_queue, 0))
            # tele/920e8c/SENSOR (esp_now_slave) {"S0":332,"S1":0,"S2":0}
            # tele/0dd6ce/T0 (esp_status)
            # tele/1dc700/SENSOR {"Sketch":"tsunamiLight v1.0","SQ":-78,"minSQ":-90,"maxSQ":-71}
            # tele/GosundW/STATE (machine room LED lights) {"Time":"2020-08-30T10:16:28","Uptime":"22T12:28:56","UptimeSec":1945736,"Heap":31,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":7,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":24,"Signal":-88,"LinkCount":3,"Downtime":"0T00:00:18"}}
            # tele/GosundX/STATE (machine room power strip)
            # tele/GosundY/STATE (TV room light)
            # tele/shellyB/STATE (machine room ceiling fan and light) {"Time":"2020-08-30T10:14:45","Uptime":"48T19:42:51","Heap":14,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"POWER1":"OFF","POWER2":"OFF","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":42,"LinkCount":10,"Downtime":"0T00:00:56"}}
            # tele/shellyB/SENSOR (machine room ceiling fan and light) {"Time":"2020-08-30T10:15:00","Switch1":"OFF","Switch2":"OFF","ANALOG":{"Temperature":100.1},"ENERGY":{"TotalStartTime":"2019-07-25T22:29:23","Total":0.586,"Yesterday":0.033,"Today":0.000,"Period":0,"Power":0,"ApparentPower":0,"ReactivePower":0,"Factor":0.00,"Voltage":0,"Current":0.000},"TempUnit":"F"}
            # tele/sonoffQ/STATE (soldering iron) {"Time":"2020-08-28T20:37:17","Uptime":"0T00:20:22","Heap":15,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"POWER":"ON","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":44,"LinkCount":1,"Downtime":"0T00:00:10"}}
            # tele/sonoffQ/SENSOR (soldering iron) {"Time":"2020-08-28T20:37:17","ENERGY":{"TotalStartTime":"2020-04-07T03:01:40","Total":0.034,"Yesterday":0.000,"Today":0.000,"Period":0,"Power":0,"ApparentPower":0,"ReactivePower":0,"Factor":0.00,"Voltage":121,"Current":0.000}}

            # go
            monitor.start()
            last_min = time.localtime().tm_min

            while True:
                try:
                    localtime = time.localtime()
                    if localtime.tm_min != last_min and 59 == localtime.tm_min:
                        # stuff to do once per hour (just before the hour strikes and the handlers clear their data)
                        for h in monitor.handlers:
                            count = h.message_count = h.messages_at_last_evaluate
                            h.publish("h.mph", f"{h.NAME} {count}")
                            h.evaluate() # do a self evaluation
                    last_min = localtime.tm_min

                    if len(metering_queue):
                        #if (isinstance(metering_queue[0], dict)
                        #    and "topic" in metering_queue[0]
                        #    and "message" in metering_queue[0]):
                        t = metering_queue[0].get("topic", "")
                        m = metering_queue[0].get("message", "")
                        f = metering_queue[0].get("filter", True)
                        if 0 == aio.publish(t, m, filter=f): # if successful handling of this message
                            metering_queue.pop(0)
                        else:
                            time.sleep(5)
                except Exception as e:
                    logging.error(f"Exception: {e}")
                    
        except Exception as e:
            logging.error(f"Exception: {e}")
            status = 1
        except KeyboardInterrupt:
            status = 2
        #except NotImplementedError:
        #    don't catch this exception
        else:
            status = 0 # if normal exit
        finally:
            # all exits
            sys.stdout.flush()
            sys.stderr.flush()
            return(status)
