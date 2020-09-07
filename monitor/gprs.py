import logging
import serial
import time
import RPi.GPIO

# states
GPRS_FOO = 0
GPRS_INITIAL = 1
GPRS_POWERING_UP = 2
GPRS_DISABLE_GPS = 3
GPRS_IP_READY = 4
GPRS_SECOND_AT = 5
GPRS_MEE = 6
GPRS_IPSPRT = 7
GPRS_CALL_READY = 8
GPRS_REGISTERED = 9
GPRS_CLK = 10
GPRS_CSQ = 11
GPRS_IPSHUT = 12
GPRS_CIICR = 13
GPRS_CSTT = 14
GPRS_CIFSR = 15
GPRS_CIPSTART = 16


# responses
GPRS_BLANK = 50
GPRS_OK = 51
GPRS_ECHO = 52
GPRS_ERROR = 53
GPRS_IPSTATUS = 54
GPRS_CALR = 55
GPRS_REG = 56
GPRS_SQ = 57
GPRS_SHUTOK = 58
GPRS_TIME = 59
GPRS_SPONTANEOUS = 60


class Gprs:
    def __init__(self, port):
        self.port = port
        self.state = GPRS_INITIAL
        self.next_state = GPRS_FOO
        self.radio_busy = False
        self.ser = None
        self.bytes = b''
        self.timeout = 0
        self.response_list = []
        self.command = ''
        self.call_ready = False
        self.registered = False
        self.signal = 0
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
        if (GPRS_BLANK == token):
            return 'blank'
        elif (GPRS_OK == token):
            return 'OK'
        elif (GPRS_ERROR == token):
            return 'ERROR'
        elif (GPRS_ECHO == token):
            return self.command
        elif (GPRS_IPSTATUS == token):
            return 'IP STATUS'
        elif (GPRS_CALR == token):
            return 'CALR'
        elif (GPRS_REG == token):
            return 'REG'
        elif (GPRS_SQ == token):
            return 'SQ'
        elif (GPRS_SHUTOK == token):
            return 'SHUT OK'
        elif (GPRS_TIME == token):
            return 'TIME'

        elif (GPRS_INITIAL == token):
            return 'GPRS_INITIAL'
        elif (GPRS_POWERING_UP == token):
            return 'GPRS_POWERING_UP'
        elif (GPRS_DISABLE_GPS == token):
            return 'GPRS_DISABLE_GPS'
        elif (GPRS_FOO == token):
            return 'GPRS_FOO'
        elif (GPRS_SECOND_AT == token):
            return 'GPRS_SECOND_AT'
        elif (GPRS_MEE == token):
            return 'GPRS_MEE'
        elif (GPRS_IPSPRT == token):
            return 'GPRS_IPSPRT'
        elif (GPRS_CALL_READY == token):
            return 'GPRS_CALL_READY'
        elif (GPRS_REGISTERED == token):
            return 'GPRS_REGISTERED'
        elif (GPRS_CLK == token):
            return 'GPRS_CLK'
        elif (GPRS_CSQ == token):
            return 'GPRS_CSQ'
        elif (GPRS_IPSHUT == token):
            return 'GPRS_IPSHUT'
        elif (GPRS_IP_READY == token):
            return 'GPRS_IP_READY'
        elif (GPRS_CIICR == token):
            return 'GPRS_CIICR'
        elif (GPRS_CIFSR == token):
            return 'GPRS_CIFSR'
        elif (GPRS_CIPSTART == token):
            return 'GPRS_CIPSTART'
        elif (GPRS_CSTT == token):
            return 'GPRS_CSTT'
        elif (GPRS_SPONTANEOUS == token):
            return 'GPRS_SPONTANEOUS'
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
            if (GPRS_SPONTANEOUS == response):
                # don't match this with expected responses
                pass
            else:
                str_response = self.to_string(response)
                #logging.debug("Gprs.match_response(): found %s line", str_response)
                if 0 < len(self.response_list):
                    if response == self.response_list[0]:
                        logging.debug(f'remove {str_response} from response_list')
                        self.response_list.pop(0)
                        return True
                    else:
                        logging.error('Gprs.match_response(): found %s line where %s was expected', str_response, self.to_string(self.response_list[0]))
                        # What do we do now?
                        self.state = GPRS_FOO

                else:
                    # got a blank line while not expecting any response
                    logging.error('Gprs.match_response(): found blank line where nothing was expected')
                    self.state = GPRS_FOO

        return False

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

        if not b'\r\n' in self.bytes:
            logging.info('partial line detected')
            return False

        # try to match the response (we could refactor relative to self.command)
        logging.info(f'process_bytes {self.lines_of_response} - {self.bytes}')
        self.lines_of_response += 1
        if self.match_response(b'\r\n', GPRS_BLANK):
            pass
        elif self.is_prefix(b'AT+', pop=False):
            if self.match_response(self.command + b'\r\r\n', GPRS_ECHO):
                pass
            else:
                logging.info(f"got AT+ prefix but not {self.command}\\r\\r\\n")
                return False
        elif self.is_prefix(b'AT', pop=False):
            if self.match_response(b'AT\r\r\n', GPRS_ECHO):
                pass
            else:
                logging.error("AT prefix, but not AT\\r\\r\\n")
                return False
        elif self.match_response(b'OK\r\n', GPRS_OK):
            pass
        elif self.match_response(b'SHUT OK\r\n', GPRS_SHUTOK):
            pass
        elif self.match_response(b'STATE: IP INITIAL\r\n', GPRS_IPSTATUS):
            self.next_state = GPRS_CSTT
        elif self.match_response(b'STATE: IP START\r\n', GPRS_IPSTATUS):
            self.next_state = GPRS_CIICR
        elif self.match_response(b'STATE: IP GPRSACT\r\n', GPRS_IPSTATUS):
            self.next_state = GPRS_CIFSR
        elif self.match_response(b'STATE: IP STATUS\r\n', GPRS_IPSTATUS):
            self.next_state = GPRS_CIPSTART
        elif self.match_response(b'STATE: TCP CLOSED\r\n', GPRS_IPSTATUS):
            #sendATCommand("AT+CIICR", 2, 15.0)
            pass
        elif self.match_response(b'STATE: IP CONFIG\r\n', GPRS_IPSTATUS):
            #time.sleep(3)
            pass
        elif self.match_response(b'STATE: TCP CONNECTING\r\n', GPRS_IPSTATUS):
            #time.sleep(10)
            pass
        elif self.match_response(b'STATE: TCP CLOSING\r\n', GPRS_IPSTATUS):
            pass
        elif self.match_response(b'STATE: PDP DEACT\r\n', GPRS_IPSTATUS):
            # what do I do?
            pass
        elif self.match_response(b'CONNECT OK\r\n', GPRS_IPSTATUS):
            # waitCONNACK()
            pass
        elif self.match_response(b'+CCALR: 0\r\n', GPRS_CALR):
            self.call_ready = False
        elif self.match_response(b'+CCALR: 1\r\n', GPRS_CALR):
            self.call_ready = True
        elif self.match_response(b'+CREG: 0,0\r\n', GPRS_REG):
            self.registered = False
        elif self.match_response(b'+CREG: 0,1\r\n', GPRS_REG):
            self.registered = True
        elif self.match_response(b'+CREG: 0,5\r\n', GPRS_REG): # roaming
            self.registered = True

        elif self.match_response(b'+CCLK: "', GPRS_TIME, partial=True):            
            temp = self.remainder.decode(encoding='UTF-8').split(',') # yy/MM/dd,hh:mm:ss+zz"
            # temp[0] is yy/MM/dd
            # temp[1] is hh:mm:ss+zz"
            logging.info("Time is %s", temp[1][0:-1])

        elif self.match_response(b'+CSQ: ', GPRS_SQ, partial=True):
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
        elif self.match_response(b'+PDP: DEACT\r\n', GPRS_SPONTANEOUS):
            pass # self.state = GPRS_FOO
        elif self.match_response(b'ERROR\r\n', GPRS_ERROR):
            self.state = GPRS_FOO

        else:
            logging.error('Gprs.process_bytes(): write code to handle %s', self.bytes)
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
            if GPRS_INITIAL == self.state:
                if not RPi.GPIO.input(7):
                    # Pull the power pin low for three seconds
                    RPi.GPIO.output(31, RPi.GPIO.LOW)
                    logging.info('The radio is OFF.  Pulling pwrkey low... ')
                    self.start_time = time.time()
                    self.state = GPRS_POWERING_UP
                else:
                    # Open the serial port
                    self.ser = serial.Serial(self.port, 115200)
                    if None == self.ser:
                        logging.error('Unable to open serial port %s', self.port)
                    else:
                        # Send a command to the radio to see if it is working
                        self.send_command(b'AT', (), [GPRS_ECHO, GPRS_OK], 5, GPRS_DISABLE_GPS)

            elif GPRS_POWERING_UP == self.state:
                if 3 <= (time.time() - self.start_time):
                    RPi.GPIO.output(31, RPi.GPIO.HIGH)
                    logging.info('Releasing pwrkey')
                    self.state = GPRS_INITIAL

            elif GPRS_DISABLE_GPS == self.state:
                self.send_command(b'AT+CGNSTST=0', (), [GPRS_ECHO, GPRS_OK], 0.5, GPRS_SECOND_AT)
            elif GPRS_SECOND_AT == self.state:
                self.send_command(b'AT', (), [GPRS_ECHO, GPRS_OK], 0.5, GPRS_MEE)
            elif GPRS_MEE == self.state:
                self.send_command(b'AT+CMEE=1', (), [GPRS_ECHO, GPRS_OK], 0.5, GPRS_IPSPRT)
            elif GPRS_IPSPRT == self.state:
                self.call_ready = False
                self.send_command(b'AT+CIPSPRT=0', (), [GPRS_ECHO, GPRS_OK], 0.5, GPRS_CALL_READY)
            elif GPRS_CALL_READY == self.state:
                if self.call_ready:
                    self.state = GPRS_REGISTERED
                    self.registered = False
                else:
                    self.send_command(b'AT+CCALR?', (), [GPRS_ECHO, GPRS_CALR, GPRS_BLANK, GPRS_OK], 0.5, GPRS_CALL_READY)
            elif GPRS_REGISTERED == self.state:
                if self.registered:
                    self.state = GPRS_CLK
                else:
                    self.send_command(b'AT+CREG?', (), [GPRS_ECHO, GPRS_REG, GPRS_BLANK, GPRS_OK], 0.5, GPRS_REGISTERED)
            elif GPRS_CLK == self.state:
                self.signal = 0
                self.send_command(b'AT+CCLK?', (), [GPRS_ECHO, GPRS_TIME, GPRS_BLANK, GPRS_OK], 0.5, GPRS_CSQ)
            elif GPRS_CSQ == self.state:
                if 4 < self.signal:
                    self.state = GPRS_IPSHUT
                else:
                    self.send_command(b'AT+CSQ', (), [GPRS_ECHO, GPRS_SQ, GPRS_BLANK, GPRS_OK], 0.5, GPRS_CSQ)
            elif GPRS_IPSHUT == self.state:
                self.send_command(b'AT+CIPSHUT', (), [GPRS_ECHO, GPRS_SHUTOK], 15, GPRS_IP_READY)
            elif GPRS_IP_READY == self.state:
                self.send_command(b'AT+CIPSTATUS', (), [GPRS_ECHO, GPRS_OK, GPRS_BLANK, GPRS_IPSTATUS], 0.5, GPRS_IP_READY)
            elif GPRS_CSTT == self.state:
                self.send_command(b'AT+CSTT="m2mglobal"', (), [GPRS_ECHO, GPRS_OK], 0.5, GPRS_IP_READY)
            elif GPRS_CIICR == self.state:
                self.send_command(b'AT+CIICR', (), [GPRS_ECHO, GPRS_OK], 65.0, GPRS_IP_READY)
            elif GPRS_CIFSR == self.state:
                self.send_command(b'AT+CIFSR', (), [GPRS_ECHO, GPRS_OK], 2.5, GPRS_IP_READY)
            elif GPRS_CIPSTART == self.state:
                self.send_command(b'AT+CIPSTART="TCP","io.adafruit.com","1883"', (), [GPRS_ECHO, GPRS_OK, GPRS_BLANK, GPRS_IPSTATUS], 65.0, GPRS_IP_READY)
            else:
                # unknown state
                logging.error('Write code to handle state %s', self.to_string(self.state))

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
