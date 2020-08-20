#!/usr/bin/env python3
# This script monitors topics in my local MQTT broker
# Some messages are forwarded to io.adafruit.com
# HTML files for the status of devices are created
import logging
import time
import sys
from mqtt.Mqtt import MqttMonitor
from handler.Handler import Garage, Laser
from adafruit.Adafruit import Adafruit
from .private import password

def main():
    logging.basicConfig(level=logging.INFO)
    # configure device handlers
    metering_queue = []
    garage = Garage("tele/99e934/SENSOR", metering_queue)
    laser = Laser("tele/sonoffP/SENSOR", metering_queue)
    #garage.dump_info()
    #laser.dump_info()
    aio = Adafruit('pmacdougal', password)

    try:
        # create an MQTT monitor and set up the topics being monitored
        monitor = MqttMonitor("192.168.2.30")
        monitor.topic(garage.topic, garage)
        monitor.topic(laser.topic, laser)
        # go
        monitor.start()

        while True:
            if len(metering_queue):
                #if (isinstance(metering_queue[0], dict)
                #    and "topic" in metering_queue[0]
                #    and "message" in metering_queue[0]):
                t = metering_queue[0].get("topic", "")
                m = metering_queue[0].get("message", "")
                aio.publish(t, m)
                metering_queue.remove()
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