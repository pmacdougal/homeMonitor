#!/usr/bin/env python3
from socket import gethostname
from monitor.monitor import Home

def main():
    hostname = gethostname()
    return Home().run(f"start Home from {hostname}", "192.168.2.30")

# This is not a module, so run the main routine when executed
if __name__ == '__main__':
    main()
