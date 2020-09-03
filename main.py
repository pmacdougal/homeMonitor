#!/usr/bin/env python3
from socket import gethostname
from monitor.monitor import Home, Barn

def main():
    if False:
        home = Home()
        hostname = gethostname()
        home.run(f"start Home from {hostname}", "h.mqtt", "192.168.2.30")
    else:
        barn = Barn()
        hostname = gethostname()
        barn.run(f"start Barn from {hostname}", "s.mqtt", "192.168.2.30")

# This is not a module, so run the main routine when executed
if __name__ == '__main__':
    main()
