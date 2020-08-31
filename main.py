from socket import gethostname
from monitor.monitor import Monitor

def main():
    hostname = gethostname()
    return Monitor().run(f"start Monitor from {hostname}")

# This is not a module, so run the main routine when executed
if __name__ == '__main__':
    main()
