# This script monitors topics in my local MQTT broker
# Some messages are forwarded to io.adafruit.com
import logging
import time
import sys
from .mqtt import MqttMonitor
from .handler import Generic, GenericEnergy, GenericString
from .adafruit import Adafruit
from .private import username, password
# private.py is not part of the checked in code.  You will need to create it.
# It is a two line file with your Adafruit IO username and access key in it:
#     username = 'xxxxxxxx'
#     password = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'

class Monitor:
    def __init__(self):
        # must be overridden
        self.access = 'foo'
        raise NotImplementedError

    def configure(self, mqtt_monitor, metering_queue):
        # must be overridden
        raise NotImplementedError

    def run(self, msg, topic, mqtt_ip):
        metering_queue = []
        metering_queue.append({'topic': topic, 'message': msg})

        try:
            aio = Adafruit(username, password, self.access)
            mqtt_monitor = MqttMonitor(mqtt_ip)
            self.configure(mqtt_monitor, metering_queue) # configure device handlers
            mqtt_monitor.start()
            last_min = time.localtime().tm_min

            while True:
                try:
                    localtime = time.localtime()
                    if localtime.tm_min != last_min and 59 == localtime.tm_min:
                        # stuff to do once per hour (just before the hour strikes and the handlers clear their data)
                        for h in mqtt_monitor.handlers:
                            h.evaluate() # do a self evaluation
                    last_min = localtime.tm_min

                    if len(metering_queue):
                        #if (isinstance(metering_queue[0], dict)
                        #and 'topic' in metering_queue[0]
                        #and 'message' in metering_queue[0]:
                        t = metering_queue[0].get('topic', '')
                        m = metering_queue[0].get('message', '')
                        s = metering_queue[0].get('state', Adafruit.INITIAL)
                        f = metering_queue[0].get('filter', True)
                        newstate = aio.publish(t, m, s, f)
                        if Adafruit.PUBLISHED == newstate:
                            logging.debug('Monitor.run() popping metering_queue entry %s', t)
                            metering_queue.pop(0)
                        elif Adafruit.INFLIGHT == newstate:
                            logging.debug('Monitor.run() updating metering_queue[0] to state INFLIGHT')
                            metering_queue[0]['state'] = newstate
                        elif Adafruit.ERROR == newstate:
                            # abandon this entry
                            logging.debug('Monitor.run() ERROR: Discarding metering_queue entry %s', t)
                            metering_queue.pop(0)
                            # delay here?
                        elif Adafruit.INITIAL == newstate:
                            # this is wierd... I guess we do nothing and let it try again
                            pass
                        else:
                            # this should never happen.  It means I am missing a case
                            logging.debug('Monitor.run() updating metering_queue[0] to state %d', newstate)
                            metering_queue[0]['state'] = newstate
                            
                    else:
                        aio.loop()
                except Exception as e:
                    logging.error('Exception: %s', e, exc_info=True)

        except Exception as e:
            logging.error('Exception: %s', e, exc_info=True)
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
            return status


class Barn(Monitor):
    '''
    Object to monitor sensors at the barn
    '''
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG)
        logging.info('Starting Barn Monitor')
        self.access = 'lte'
        #self.access = 'gprs'

    def configure(self, mqtt_monitor, metering_queue):        
        '''
        configure each of the local MQTT topics being monitored and the AdFruit Topics being published
        '''
        handler = Generic('tele/0dd92a/SENSOR', metering_queue, 240, 's.mph')
        handler.NAME = 'PumpHouse'
        handler.setup('s.ot', 'T0')
        handler.setup('s.it', 'T1')
        handler.setup('s.ht', 'HT')
        handler.setup('s.rt', 'RTCount')
        mqtt_monitor.topic(handler)

        handler = Generic('tele/0dd096/SENSOR', metering_queue, 240, 's.mph')
        handler.NAME = 'Loft'
        handler.setup('s.lt', 'T0')
        mqtt_monitor.topic(handler)

        # tele/921601/TRIP {"GCBMS":1.0,"Sketch":"ESP GCBMS coprocessor v1.0","Duration":7,"Odometer":0,"Current":0,"Speed":0,"b0":5231,"B0":5497,"b1":0,"B1":0,"b2":0,"B2":0,"b3":0,"B3":0,"b4":0,"B4":0,"b5":0,"B5":0,"StopTime":159199}
        handler = Generic('tele/921601/TRIP', metering_queue, 0, 's.mph')
        handler.NAME = 'Rriba'
        handler.setup('rriba.b0', 'b0', filter=False)
        handler.setup('rriba.b1', 'b1', filter=False)
        handler.setup('rriba.b2', 'b2', filter=False)
        handler.setup('rriba.b3', 'b3', filter=False)
        handler.setup('rriba.b4', 'b4', filter=False)
        handler.setup('rriba.b5', 'b5', filter=False)
        handler.setup('rriba.duration', 'Duration', filter=False)
        handler.setup('rriba.odometer', 'Odometer', filter=False)
        handler.setup('rriba.current', 'Current', filter=False)
        handler.setup('rriba.speed', 'Speed', filter=False)
        mqtt_monitor.topic(handler)


class Home(Monitor):
    '''
    Object to monitor sensors at home
    '''
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.access = 'rest'

    def configure(self, mqtt_monitor, metering_queue):
        '''
        configure each of the local MQTT topics being monitored and the AdaFruit Topics being published
        '''
        handler = Generic('tele/99e934/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'Garage'
        handler.setup('g.sq',  'SQ')
        handler.setup('g.door', 'doorCount')
        handler.setup('g.t0',  'T0')
        handler.setup('g.t1',  'T1')
        mqtt_monitor.topic(handler)

        handler = Generic('tele/3154ff/SENSOR', metering_queue, 1, 'h.mph')
        handler.NAME = 'SoilProbe'
        handler.setup('h.sp',  'S0')
        handler.setup('h.sb',  'S1')
        mqtt_monitor.topic(handler)

        handler = Generic('tele/99e813/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'Waterer'
        handler.setup('h.r', 'RTCount')
        handler.setup('h.v', 'valveCount')
        handler.setup('h.vr', 'VBATLOAD')
        handler.setup('w.valve', 'valveCount')
        handler.setup('w.vbat', 'VBATLOAD')
        mqtt_monitor.topic(handler)

        handler = GenericString('tele/99e813/VOT', metering_queue, 0, 'h.mph')
        handler.NAME = 'watererValve'
        handler.setup('w.vot', 'unused')
        mqtt_monitor.topic(handler)

        handler = GenericString('tele/99e813/VCT', metering_queue, 0, 'h.mph')
        handler.NAME = 'watererValve'
        handler.setup('w.vct', 'unused')
        mqtt_monitor.topic(handler)

        handler = Generic('tele/9215de/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'CatFeeder'
        handler.setup('h.cf', 'CFCount')
        mqtt_monitor.topic(handler)

        handler = GenericEnergy('tele/sonoffP/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'Laser'
        handler.setup('h.lasercurrent', 'Current')
        mqtt_monitor.topic(handler)

        handler = GenericEnergy('tele/sonoffD/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'Printer'
        handler.setup('h.printercurrent', 'Current', clamp=0.150)
        mqtt_monitor.topic(handler)

        handler = GenericEnergy('tele/sonoffE/SENSOR', metering_queue, 240, 'h.mph')
        handler.NAME = 'Washer'
        handler.setup('h.washercurrent', 'Current', clamp=0.06)
        handler.setup('h.washervoltage', 'Voltage')
        mqtt_monitor.topic(handler)

        handler = GenericString('ups', metering_queue, 0, 'h.mph')
        handler.NAME = 'Ups'
        handler.setup('h.ups', 'unused')
        mqtt_monitor.topic(handler)

        handler = GenericString('tele/0dd6ce/wce', metering_queue, 0, 'h.mph')
        handler.NAME = 'Status'
        handler.setup('h.wce', 'unused')
        mqtt_monitor.topic(handler)

        # tele/920e8c/SENSOR (esp_now_slave) {"S0":332,"S1":0,"S2":0}
        # tele/1dc700/SENSOR {"Sketch":"tsunamiLight v1.0","SQ":-78,"minSQ":-90,"maxSQ":-71}
        # tele/GosundW/STATE (machine room LED lights) {"Time":"2020-08-30T10:16:28","Uptime":"22T12:28:56","UptimeSec":1945736,"Heap":31,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"MqttCount":7,"POWER":"OFF","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":24,"Signal":-88,"LinkCount":3,"Downtime":"0T00:00:18"}}
        # tele/GosundX/STATE (machine room power strip)
        # tele/GosundY/STATE (TV room light)
        # tele/shellyB/STATE (machine room ceiling fan and light) {"Time":"2020-08-30T10:14:45","Uptime":"48T19:42:51","Heap":14,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"POWER1":"OFF","POWER2":"OFF","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":42,"LinkCount":10,"Downtime":"0T00:00:56"}}
        # tele/shellyB/SENSOR (machine room ceiling fan and light) {"Time":"2020-08-30T10:15:00","Switch1":"OFF","Switch2":"OFF","ANALOG":{"Temperature":100.1},"ENERGY":{"TotalStartTime":"2019-07-25T22:29:23","Total":0.586,"Yesterday":0.033,"Today":0.000,"Period":0,"Power":0,"ApparentPower":0,"ReactivePower":0,"Factor":0.00,"Voltage":0,"Current":0.000},"TempUnit":"F"}
        # tele/sonoffQ/STATE (soldering iron) {"Time":"2020-08-28T20:37:17","Uptime":"0T00:20:22","Heap":15,"SleepMode":"Dynamic","Sleep":50,"LoadAvg":19,"POWER":"ON","Wifi":{"AP":1,"SSId":"Cisco52305","BSSId":"68:7F:74:49:E3:7E","Channel":6,"RSSI":44,"LinkCount":1,"Downtime":"0T00:00:10"}}
        # tele/sonoffQ/SENSOR (soldering iron) {"Time":"2020-08-28T20:37:17","ENERGY":{"TotalStartTime":"2020-04-07T03:01:40","Total":0.034,"Yesterday":0.000,"Today":0.000,"Period":0,"Power":0,"ApparentPower":0,"ReactivePower":0,"Factor":0.00,"Voltage":121,"Current":0.000}}
