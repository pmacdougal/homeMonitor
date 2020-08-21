#!/usr/bin/env python3
# This script monitors topics in my local MQTT broker
# Some messages are forwarded to io.adafruit.com
# HTML files for the status of devices are created
import logging
import time
import sys
from mqtt.Mqtt import MqttMonitor
from handler.Handler import Garage, Laser, SoilProbe, Waterer, Printer, Washer
from adafruit.Adafruit import Adafruit
from private import password

def main():
    logging.basicConfig(level=logging.DEBUG)
    # configure device handlers
    metering_queue = []
    aio = Adafruit('pmacdougal', password)

    try:
        # create an MQTT monitor and set up the topics being monitored
        monitor = MqttMonitor("192.168.2.30")
        monitor.topic(Garage("tele/99e934/SENSOR", metering_queue))
        monitor.topic(Laser("tele/sonoffP/SENSOR", metering_queue))
        monitor.topic(SoilProbe('tele/3154ff/SENSOR', metering_queue))
        monitor.topic(Waterer('tele/99e813/SENSOR', metering_queue))
        monitor.topic(Printer('tele/sonoffD/SENSOR', metering_queue))
        monitor.topic(Washer('tele/sonoffE/SENSOR', metering_queue))
        # go
        monitor.start()

        while True:
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
        exit(status)

# This is not a module, so run the main routine when executed
if __name__ == '__main__':
    main()