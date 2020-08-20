#!/usr/bin/env python3
# This script monitors topics in my local MQTT broker
# Some messages are forwarded to io.adafruit.com
# HTML files for the status of devices are created
import logging
import time
import sys
from mqtt.Mqtt import MqttMonitor
from handler.Handler import Garage, Laser

def main():
    logging.basicConfig(level=logging.INFO)
    # configure device handlers
    metering_queue = []
    garage = Garage("tele/99e934/SENSOR", metering_queue)
    laser = Laser("tele/sonoffP/SENSOR", metering_queue)
    #garage.dump_info()
    #laser.dump_info()

    try:
        # create an MQTT monitor and set up the topics being monitored
        monitor = MqttMonitor("192.168.2.30")
        monitor.topic(garage.topic, garage)
        monitor.topic(laser.topic, laser)
        # go
        monitor.go()

        while True:
            if len(metering_queue):
                if (isinstance(metering_queue[0], dict)
                    and "topic" in metering_queue[0]
                    and "message" in metering_queue[0]):
                    foo = metering_queue[0].get("topic", "")
                    bar = metering_queue[0].get("message", "")
                    if "" != foo:
                        # send bar to foo
                 metering_queue.remove()
                
            time.sleep(120)
            print(len(metering_queue))
            # ping io.adafruit.com to say we are up and running
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