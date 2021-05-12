#!/usr/bin/env python3
from socket import gethostname
from time import sleep
from .monitor.monitor import Home, Barn

def main():
    while True:
        if True:
            home = Home()
            hostname = gethostname()
            status = home.run(f'start Home from {hostname}', 'h.mqtt', '192.168.2.30')
            # status is ignored
        else:
            barn = Barn()
            hostname = gethostname()
            status = barn.run(f'start Barn from {hostname}', 's.mqtt', '192.168.2.32')
            # status is ignored
        sleep(60)



# This is not a module, so run the main routine when executed
if __name__ == '__main__':
    main()
