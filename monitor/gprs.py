import logging
import serial
import time
import RPi.GPIO
from socket import gethostname
from monitor.private import username, password

# states
GPRS_STATE_MAX = 0
GPRS_STATE_FOO = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_INITIAL = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_POWERING_UP = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_DISABLE_GPS = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_IP_READY = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_SECOND_AT = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_MEE = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_IPSPRT = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CALL_READY = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_REGISTERED = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CLK = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CSQ = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_IPSHUT = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CIICR = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CSTT = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CIFSR = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CIPSTART = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
GPRS_STATE_CONNECT = GPRS_STATE_MAX; GPRS_STATE_MAX += 1
#GPRS_STATE_WAIT_CONNACK = GPRS_STATE_MAX; GPRS_STATE_MAX += 1




# responses
GPRS_RESPONSE_BLANK = 50
GPRS_RESPONSE_OK = 51
GPRS_RESPONSE_ECHO = 52
GPRS_RESPONSE_ERROR = 53
GPRS_RESPONSE_IPSTATUS = 54
GPRS_RESPONSE_CALR = 55
GPRS_RESPONSE_REG = 56
GPRS_RESPONSE_SQ = 57
GPRS_RESPONSE_SHUTOK = 58
GPRS_RESPONSE_TIME = 59
GPRS_RESPONSE_SPONTANEOUS = 60
GPRS_RESPONSE_IPADDR = 61
GPRS_RESPONSE_CONNACK = 62
GPRS_RESPONSE_SENDOK = 63

class Gprs_state:
    def __init__(self, machine, response_list, response_count, next_state, command_string):
        self.machine = machine
        self.response_list = response_list
        self.response_count = response_count
        self.next_state = next_state
        self.command_string = command_string
        pass



class Gprs:
    def __init__(self, port):
        self.port = port
        self.state = GPRS_STATE_INITIAL
        self.next_state = GPRS_STATE_FOO
        self.radio_busy = False
        self.ser = None
        self.bytes = b''
        self.timeout = 0
        self.response_list = []
        self.command = ''
        self.call_ready = False
        self.registered = False
        self.signal = 0
        self.state_list = [None]*GPRS_STATE_MAX
        
        self.state_list[GPRS_STATE_INITIAL] = Gprs_state(self, b'AT', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 5, GPRS_STATE_DISABLE_GPS)



        #set numbering mode for the program
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        RPi.GPIO.setwarnings(False)        
        RPi.GPIO.setup(7, RPi.GPIO.IN)
        RPi.GPIO.setup(31, RPi.GPIO.OUT)

    # read bytes from serial port concatenating them into an internal tuple of bytes
    def check_input(self):
        if None != self.ser and 0 < self.ser.in_waiting:
            self.ser.timeout = self.timeout
            newbytes = self.ser.read_until(terminator=b'\r\n')
            self.bytes += newbytes

    # convert constants to string representations
    def to_string(self, token):
        if GPRS_RESPONSE_BLANK == token:
            return 'blank'
        elif GPRS_RESPONSE_OK == token:
            return 'OK'
        elif GPRS_RESPONSE_ERROR == token:
            return 'ERROR'
        elif GPRS_RESPONSE_ECHO == token:
            return self.command
        elif GPRS_RESPONSE_IPSTATUS == token:
            return 'IP STATUS'
        elif GPRS_RESPONSE_CALR == token:
            return 'CALR'
        elif GPRS_RESPONSE_REG == token:
            return 'REG'
        elif GPRS_RESPONSE_SQ == token:
            return 'SQ'
        elif GPRS_RESPONSE_SHUTOK == token:
            return 'SHUT OK'
        elif GPRS_RESPONSE_TIME == token:
            return 'TIME'
        elif GPRS_RESPONSE_SPONTANEOUS == token:
            return 'GPRS_RESPONSE_SPONTANEOUS'
        elif GPRS_RESPONSE_IPADDR == token:
            return 'GPRS_RESPONSE_IPADDR'
        elif GPRS_RESPONSE_CONNACK == token:
            return 'GPRS_RESPONSE_CONNACK'
        elif GPRS_RESPONSE_SENDOK == token:
            return 'GPRS_RESPONSE_SENDOK'

        elif GPRS_STATE_INITIAL == token:
            return 'GPRS_STATE_INITIAL'
        elif GPRS_STATE_POWERING_UP == token:
            return 'GPRS_STATE_POWERING_UP'
        elif GPRS_STATE_DISABLE_GPS == token:
            return 'GPRS_STATE_DISABLE_GPS'
        elif GPRS_STATE_FOO == token:
            return 'GPRS_STATE_FOO'
        elif GPRS_STATE_SECOND_AT == token:
            return 'GPRS_STATE_SECOND_AT'
        elif GPRS_STATE_MEE == token:
            return 'GPRS_STATE_MEE'
        elif GPRS_STATE_IPSPRT == token:
            return 'GPRS_STATE_IPSPRT'
        elif GPRS_STATE_CALL_READY == token:
            return 'GPRS_STATE_CALL_READY'
        elif GPRS_STATE_REGISTERED == token:
            return 'GPRS_STATE_REGISTERED'
        elif GPRS_STATE_CLK == token:
            return 'GPRS_STATE_CLK'
        elif GPRS_STATE_CSQ == token:
            return 'GPRS_STATE_CSQ'
        elif GPRS_STATE_IPSHUT == token:
            return 'GPRS_STATE_IPSHUT'
        elif GPRS_STATE_IP_READY == token:
            return 'GPRS_STATE_IP_READY'
        elif GPRS_STATE_CIICR == token:
            return 'GPRS_STATE_CIICR'
        elif GPRS_STATE_CIFSR == token:
            return 'GPRS_STATE_CIFSR'
        elif GPRS_STATE_CIPSTART == token:
            return 'GPRS_STATE_CIPSTART'
        elif GPRS_STATE_CSTT == token:
            return 'GPRS_STATE_CSTT'
        elif GPRS_STATE_CONNECT == token:
            return 'GPRS_STATE_CONNECT'
        #elif GPRS_STATE_WAIT_CONNACK == token:
        #    return 'GPRS_STATE_WAIT_CONNACK'
        else:
            raise NotImplementedError

    # see if the string parameter is at the beginning of the recieved bytes from the radio
    def is_prefix(self, string, *, pop=False):
        if string == self.bytes[0:len(string)]:
            if (pop):
                self.bytes = self.bytes[len(string):]
            return True
        else:
            #logging.info(f"{string} is not a prefix of {self.bytes}")
            return False

    # see if the radio responded with the expected response
    def match_response(self, string, response, *, partial=False):
        if self.is_prefix(string, pop=True):
            if partial:
                pos = self.bytes.find(b'\r\n')
                #logging.info("%s End of line is at %d", self.bytes, pos)
                if -1 == pos:
                    raise NotImplementedError
                self.remainder = self.bytes[0:pos]
                self.clear_to_end_of_line()

            # match with the expected response
            if (GPRS_RESPONSE_SPONTANEOUS == response):
                # don't match this with expected responses
                pass
            else:
                str_response = self.to_string(response)
                #logging.debug("Gprs.match_response(): found %s line", str_response)
                if 0 < len(self.response_list):
                    if response == self.response_list[0]:
                        #logging.debug(f'remove {str_response} from response_list')
                        self.response_list.pop(0)
                        return True
                    else:
                        logging.error('Gprs.match_response(): found %s line where %s was expected', str_response, self.to_string(self.response_list[0]))
                        # What do we do now?
                        self.state = GPRS_STATE_FOO

                else:
                    # got a blank line while not expecting any response
                    logging.error('Gprs.match_response(): found blank line where nothing was expected')
                    self.state = GPRS_STATE_FOO

        return False

    # remove bytes until we reach \r\n
    def clear_to_end_of_line(self):
        pos = self.bytes.find(b'\r\n')
        #logging.info("%s End of line is at %d", self.bytes, pos)
        if -1 == pos:
            raise NotImplementedError
        self.bytes = self.bytes[pos+2:]
       
    # match bytes from the radio with expected responses
    def process_bytes(self):
        # if there is no response from radio, just return
        if (0 == len(self.bytes)):
            return False

        # handle responses that do not end with \r\n (tyically MQTT packets)
        if GPRS_RESPONSE_CONNACK == self.response_list[0]:
            if 4 <= len(self.bytes):
                # opcode 32
                # length - 2
                # session present - 0 or 1
                # payload - 0, 1, 2, 3, 4, 5
                if (b' ' == self.bytes[0]
                   and b'\x02' == self.bytes[1]
                   and (b'\x00' == self.bytes[2] or b'\x01' == self.bytes[2])):
                    if b'\x00' == self.bytes[3]:
                        logging.info("Got CONNACK from MQTT broker")
                        self.response_list.pop(0)
                        self.bytes = self.bytes[4:]
                    else:
                        logging.error('CONNACK connection refused.  Status %s', self.bytes[3])
                        self.state = GPRS_STATE_FOO 

        if not b'\r\n' in self.bytes:
            logging.info('partial line detected %d %s', len(self.bytes), self.bytes)
            return False

        # try to match the response (we could refactor relative to self.command)
        logging.info(f'Gprs.process_bytes() {self.lines_of_response} - {self.bytes}')
        self.lines_of_response += 1
        if self.match_response(b'\r\n', GPRS_RESPONSE_BLANK):
            pass
        elif self.is_prefix(b'AT+', pop=False):
            if self.match_response(self.command + b'\r\r\n', GPRS_RESPONSE_ECHO):
                pass
            else:
                logging.info(f"got AT+ prefix but not {self.command}\\r\\r\\n")
                return False
        elif self.is_prefix(b'AT', pop=False):
            if self.match_response(b'AT\r\r\n', GPRS_RESPONSE_ECHO):
                pass
            else:
                logging.error("AT prefix, but not AT\\r\\r\\n")
                return False
        elif self.match_response(b'OK\r\n', GPRS_RESPONSE_OK):
            pass
        elif self.match_response(b'SHUT OK\r\n', GPRS_RESPONSE_SHUTOK):
            pass
        elif self.match_response(b'STATE: IP INITIAL\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = GPRS_STATE_CSTT
        elif self.match_response(b'STATE: IP START\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = GPRS_STATE_CIICR
        elif self.match_response(b'STATE: IP GPRSACT\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = GPRS_STATE_CIFSR
        elif self.match_response(b'STATE: IP STATUS\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = GPRS_STATE_CIPSTART
        elif self.match_response(b'STATE: TCP CLOSED\r\n', GPRS_RESPONSE_IPSTATUS):
            #sendATCommand("AT+CIICR", 2, 15.0)
            pass
        elif self.match_response(b'STATE: IP CONFIG\r\n', GPRS_RESPONSE_IPSTATUS):
            #time.sleep(3)
            pass
        elif self.match_response(b'STATE: TCP CONNECTING\r\n', GPRS_RESPONSE_IPSTATUS):
            #time.sleep(10)
            pass
        elif self.match_response(b'STATE: TCP CLOSING\r\n', GPRS_RESPONSE_IPSTATUS):
            pass
        elif self.match_response(b'STATE: PDP DEACT\r\n', GPRS_RESPONSE_IPSTATUS):
            # what do I do?
            pass
        elif self.match_response(b'CONNECT OK\r\n', GPRS_RESPONSE_IPSTATUS):
            # self.next_state = GPRS_STATE_WAIT_CONNACK
            # waitCONNACK()
            pass
        elif self.match_response(b'+CCALR: 0\r\n', GPRS_RESPONSE_CALR):
            self.call_ready = False
        elif self.match_response(b'+CCALR: 1\r\n', GPRS_RESPONSE_CALR):
            self.call_ready = True
        elif self.match_response(b'+CREG: 0,0\r\n', GPRS_RESPONSE_REG):
            self.registered = False
        elif self.match_response(b'+CREG: 0,1\r\n', GPRS_RESPONSE_REG):
            self.registered = True
        elif self.match_response(b'+CREG: 0,5\r\n', GPRS_RESPONSE_REG): # roaming
            self.registered = True

        elif self.match_response(b'+CCLK: "', GPRS_RESPONSE_TIME, partial=True):            
            temp = self.remainder.decode(encoding='UTF-8').split(',') # yy/MM/dd,hh:mm:ss+zz"
            # temp[0] is yy/MM/dd
            # temp[1] is hh:mm:ss+zz"
            logging.info("Time is %s", temp[1][0:-1])

        elif self.match_response(b'+CSQ: ', GPRS_RESPONSE_SQ, partial=True):
            temp = self.remainder.decode(encoding='UTF-8').split(',')
            signal = temp[0]
            if 1 == len(signal):
                self.signal = ord(signal[0]) - ord(b'0')
            elif 2 == len(signal):
                self.signal = (ord(signal[0]) - ord(b'0'))*10 + (ord(signal[1]) - ord(b'0'))
            else:
                logging.error("This is unexpected.  len(signal) is %s", len(signal))
                self.signal = 0
            logging.info("Signal quality is %d", self.signal)

        # Error conditions
        elif self.match_response(b'+PDP: DEACT\r\n', GPRS_RESPONSE_SPONTANEOUS):
            pass # self.state = GPRS_STATE_FOO
        elif self.match_response(b'ERROR\r\n', GPRS_RESPONSE_ERROR):
            self.state = GPRS_STATE_FOO

        # hard to identify things (need regex or some such)
        elif GPRS_RESPONSE_IPADDR == self.response_list[0]:
            temp = self.bytes.decode(encoding='UTF-8').split('.') # xxx.xxx.xxx.xxx"
            if 4 == len(temp):
                logging.info("IP Address is %s.%s.%s.%s", temp[0], temp[1], temp[2], temp[3])
                self.response_list.pop(0)
                self.clear_to_end_of_line()
            else:
                logging.error("Failed to parse line that should have been an IP address: %s", self.bytes)
                self.state = GPRS_STATE_FOO

        else:
            logging.error('Gprs.process_bytes(): write code to handle %s %d', self.bytes, len(self.bytes))
            raise NotImplementedError
            #self.clear_to_end_of_line()
            return False

        return True

    def loop(self):
        self.check_input()
        while self.process_bytes(): # this needs a timeout or iteration limit
            if 0 == len(self.response_list):
                # we have satisfied the expected response for the command
                logging.info("%s done in %d seconds. Next state %s", self.command, time.time()-self.command_start_time, self.to_string(self.next_state))
                self.radio_busy = False
                self.state = self.next_state

        if self.radio_busy:
            # wait for radio to finish current operation
            pass

        else:
            if GPRS_STATE_INITIAL == self.state:
                if not RPi.GPIO.input(7):
                    # Pull the power pin low for three seconds
                    RPi.GPIO.output(31, RPi.GPIO.LOW)
                    logging.info('The radio is OFF.  Pulling pwrkey low... ')
                    self.start_time = time.time()
                    self.state = GPRS_STATE_POWERING_UP
                else:
                    # Open the serial port
                    self.ser = serial.Serial(self.port, 115200)
                    if None == self.ser:
                        logging.error('Unable to open serial port %s', self.port)
                    else:
                        # Send a command to the radio to see if it is working
                        self.send_command(b'AT', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 5, GPRS_STATE_DISABLE_GPS)

            elif GPRS_STATE_POWERING_UP == self.state:
                if 3 <= (time.time() - self.start_time):
                    RPi.GPIO.output(31, RPi.GPIO.HIGH)
                    logging.info('Releasing pwrkey')
                    self.state = GPRS_STATE_INITIAL

            elif GPRS_STATE_DISABLE_GPS == self.state:
                self.send_command(b'AT+CGNSTST=0', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_SECOND_AT)
            elif GPRS_STATE_SECOND_AT == self.state:
                self.send_command(b'AT', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_MEE)
            elif GPRS_STATE_MEE == self.state:
                self.send_command(b'AT+CMEE=1', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_IPSPRT)
            elif GPRS_STATE_IPSPRT == self.state:
                self.call_ready = False
                self.send_command(b'AT+CIPSPRT=0', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_CALL_READY)
            elif GPRS_STATE_CALL_READY == self.state:
                if self.call_ready:
                    self.state = GPRS_STATE_REGISTERED
                    self.registered = False
                else:
                    self.send_command(b'AT+CCALR?', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_CALR, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_CALL_READY)
            elif GPRS_STATE_REGISTERED == self.state:
                if self.registered:
                    self.state = GPRS_STATE_CLK
                else:
                    self.send_command(b'AT+CREG?', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_REG, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_REGISTERED)
            elif GPRS_STATE_CLK == self.state:
                self.signal = 0
                self.send_command(b'AT+CCLK?', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_TIME, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_CSQ)
            elif GPRS_STATE_CSQ == self.state:
                if 4 < self.signal:
                    self.state = GPRS_STATE_IPSHUT
                else:
                    self.send_command(b'AT+CSQ', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SQ, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_CSQ)
            elif GPRS_STATE_IPSHUT == self.state:
                self.send_command(b'AT+CIPSHUT', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SHUTOK], 15, GPRS_STATE_IP_READY)
            elif GPRS_STATE_IP_READY == self.state:
                self.send_command(b'AT+CIPSTATUS', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_IPSTATUS], 0.5, GPRS_STATE_IP_READY)
            elif GPRS_STATE_CSTT == self.state:
                self.send_command(b'AT+CSTT="m2mglobal"', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 0.5, GPRS_STATE_IP_READY)
            elif GPRS_STATE_CIICR == self.state:
                self.send_command(b'AT+CIICR', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], 65.0, GPRS_STATE_IP_READY)
            elif GPRS_STATE_CIFSR == self.state:
                self.send_command(b'AT+CIFSR', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_IPADDR], 2.5, GPRS_STATE_IP_READY)
            elif GPRS_STATE_CIPSTART == self.state:
                self.send_command(b'AT+CIPSTART="TCP","io.adafruit.com","1883"', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_IPSTATUS], 120.0, GPRS_STATE_CONNECT)
            elif GPRS_STATE_CONNECT == self.state:
                packet = self.buildConnectPacket()
                self.send_command(b'AT+CIPSEND', packet, [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SENDOK, GPRS_RESPONSE_CONNACK], 30.0, GPRS_STATE_FOO)

            #elif GPRS_STATE_WAIT_CONNACK == self.state:
            #    self.send_command(b'AT+CIPSTART="TCP","io.adafruit.com","1883"', (), [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_IPSTATUS], 65.0, GPRS_STATE_IP_READY)
            #    self.response_list = [GPRS_RESPONSE_CONNACK]
            #    self.next_state = GPRS_STATE_FOO
            else:
                # unknown state
                logging.error('Write code to handle state %s', self.to_string(self.state))

    def buildConnectPacket(self):
        hostname = gethostname()
        # connect packet
        packet = bytearray(0)
        # Fixed Header
        packet.append(0x10) # MQTT_CTRL_CONNECT << 4
        packet.append(0) # length for now is zero
        # Protocol Name
        packet.append(0) # Protocol name length MSB
        packet.append(4) # Protocol name length LSB
        packet += b'MQTT'
        # Protocol Level
        packet.append(4) # Protocol level
        # Connect Flags
        #define MQTT_CONN_USERNAMEFLAG    0x80
        #define MQTT_CONN_PASSWORDFLAG    0x40
        #define MQTT_CONN_CLEANSESSION    0x02
        packet.append(0x80+0x40+0x02)
        # Keepalive
        packet.append(0x01) # 256
        packet.append(0x2c) #  44
        # Cliend Identifier
        packet.append(0x00) # clientId length MSB
        packet.append(len(hostname)) # clientId length LSB
        packet += hostname
        # Will Topic
        # Will Message
        # Username
        packet.append(0x00) # username length MSB
        packet.append(len(username)) # username length LSB
        packet += username
        # Password
        packet.append(0x00) # password length MSB
        packet.append(len(password)) # password length LSB
        packet += password
        # Fill in packet length
        if 127 < len(packet)-2:
            logging.error("Write more code 3")
            raise NotImplementedError
        if 28 == len(packet):
            logging.error("Write more code 4")
            raise NotImplementedError
        if 29 == len(packet):
            logging.error("Write more code 5")
            raise NotImplementedError
        packet[1] = len(packet)-2
        # GPRS MODEM end of transmission flag
        packet.append(26) # not really part of the packet
        return packet

    def send_command(self, command, bytes, response_list, timeout, next_state):
        logging.debug('Gprs.send_command(): Sending command %s', command)
        self.command = command
        self.response_list = response_list
        self.timeout = timeout
        self.next_state = next_state
        self.radio_busy = True
        self.command_start_time = time.time()
        self.lines_of_response = 0
        self.ser.write(command)
        self.ser.write(b'\r\n')
        if len(bytes):
            time.sleep(0.5)
            self.ser.write(bytes)

    def is_ready(self):
        return False

    def publish(self, topic, message):
        pass
