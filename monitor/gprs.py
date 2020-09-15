import logging
import serial
import time
import RPi.GPIO
from socket import gethostname
from monitor.private import username, password

'''
ToDo:
    implement a DELAY state
    test powering up the radio
'''

# responses
GPRS_RESPONSE_MAX = 50 # something bigger than GPRS_STATE_MAX
GPRS_RESPONSE_BLANK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_CALR = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_CONNACK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_CONNECTOK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_ECHO = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_IPADDR = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_IPSTATUS = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_OK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_ERROR = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_REG = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_SENDOK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_SHUTOK = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_SPONTANEOUS = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_SQ = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_TIME = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_MQTT = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1

class xxx(Exception):
    pass

class GprsState:
    """
    State Machine State with actions to perform and next state to transition to
    """
    def __init__(self, radio, command_string, response_list, next_state, *, prefix='', suffix='', delay=0):
        self.radio = radio
        self.command_string = command_string
        self.response_list = response_list
        self.next_state = next_state
        self.prefix = prefix
        self.suffix = suffix
        self.delay = delay
        self.packet = ()
        self.loop_count = 0

    def method_return_zero(self):
        """
        do nothing but return 0
        """
        return 0

    def method_return_one(self):
        """
        do nothing but return 1
        """
        return 1

    def method_ccr(self):
        """
        clear call ready in the radio
        """
        self.radio.call_ready = False
        self.loop_count = 0
        return 0

    def method_cr_loop(self):
        """
        if radio is ready to make a call, return 1
        """
        self.loop_count += 1
        if self.radio.call_ready:
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_REGISTERED']
            self.radio.registered = False
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning("method_cr_loop() stuck in loop")
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_FOO']
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_cr_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_reg_loop(self):
        """
        if radio is registered on the network, return 1
        """
        self.loop_count += 1
        if self.radio.registered:
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_CLK']
            self.radio.signal = 0
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning("method_reg_loop() stuck in loop")
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_FOO']
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_reg_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_sq_loop(self):
        """
        if radio has sufficient signal strength, return 1
        """
        self.loop_count += 1
        if 4 < self.radio.signal:
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_IPSHUT']
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning("method_sq_loop() stuck in loop")
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_FOO']
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_sq_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_build_connect_packet(self):
        """
        build a MQTT connect packet
        """
        self.packet = self.radio.build_connect_packet()
        return 0

    def method_keep_alive(self):
        """
        periodically, the radio needs to communicate with AdaFruit
        We publish the radio signal quality if nothing else is going on
        """
        if 240 < self.radio.loop_time - self.radio.command_start_time:
            return 0
        return 1

    def method_publish_sq(self):
        """
        publish radio strength
        always returns 1, so that we do not do a radio.send_command
        """
        self.radio.publish('s.sq', self.radio.signal)
        self.radio.previous_state = self.radio.state
        self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_PUBLISH']
        return 1

    def method_foo(self):
        """
        handle errors
        """
        logging.info('method_foo()')
        raise KeyboardInterrupt # try to exit the program here

    def method_power_up(self):
        """
        check if the radio is powered on
        open the serial port
        """
        if not RPi.GPIO.input(7):
            # Pull the power pin low for three seconds
            RPi.GPIO.output(31, RPi.GPIO.LOW)
            logging.info('The radio is OFF.  Pulling pwrkey low... ')
            self.radio.start_time = self.radio.loop_time
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_POWERING_UP']
            return 1
        else:
            # Open the serial port
            self.radio.ser = serial.Serial(self.radio.port, 115200)
            if None == self.radio.ser:
                logging.error('Unable to open serial port %s', self.radio.port)
                return 1
        return 0

    def method_power_up_delay(self):
        """
        release power button after 3 seconds
        always returns 1, so that we do not do a radio.send_command
        """
        if 3 <= (self.radio.loop_time - self.radio.start_time):
            RPi.GPIO.output(31, RPi.GPIO.HIGH)
            logging.info('Releasing pwrkey')
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_INITIAL']
        return 1

    def method_delay(self):
        """
        delay before going to next state
        always returns 1, so that we do not do a radio.send_command
        """
        if self.radio.delay_time <= (self.radio.loop_time - self.radio.start_delay_time):
            logging.debug("Advance to %s", self.radio.state_string_list[self.radio.next_state])
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.next_state
        return 1

    METHODS = {
        '': method_return_zero,
        'return_one': method_return_one,
        'clear_cr': method_ccr,
        'loop_cr': method_cr_loop,
        'loop_reg': method_reg_loop,
        'loop_sq': method_sq_loop,
        'build_connect_packet': method_build_connect_packet,
        'keep_alive': method_keep_alive,
        'publish_sq': method_publish_sq,
        'state_foo': method_foo,
        'power_up': method_power_up,
        'pu_delay': method_power_up_delay,
        'state_delay': method_delay
         }

    def run(self):
        if 'GPRS_STATE_PUBLISH' != self.radio.state_string_list[self.radio.state]:
            logging.info('### %s %s %s', self.radio.state_string_list[self.radio.state], self.prefix, self.suffix)
        ret1 = self.METHODS[self.prefix](self)
        ret2 = 0
        if 0 == ret1:
            # make a copy of the response list in case we re-visit this state
            self.radio.send_command(self.command_string, self.packet, self.response_list.copy(), self.next_state)
            ret2 = self.METHODS[self.suffix](self)
            if 0 < self.delay:
                logging.debug("Delay %d seconds before going into state %s", self.delay, self.radio.state_string_list[self.next_state])
                self.radio.previous_state = self.radio.state
                self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_DELAY']
                self.radio.start_delay_time = time.time()
                self.radio.next_state = self.next_state
                self.radio.delay_time = self.delay
            else:
                self.radio.previous_state = self.radio.state
                self.radio.state = self.next_state
        return ret1, ret2


class Gprs:
    """
    Class for GPRS radio HAT
    """
    def __init__(self, port):
        #logging.debug('Constructing Gprs object')
        self.port = port
        self.radio_busy = False
        self.ser = None
        self.bytes = b''
        self.response_list = []
        self.command = ''
        self.call_ready = False
        self.registered = False
        self.signal = 0
        self.connected = False
        self.state_string_list = (
            'GPRS_STATE_CALL_READY',
            'GPRS_STATE_CIFSR',
            'GPRS_STATE_CIICR',
            'GPRS_STATE_CIPSTART',
            'GPRS_STATE_CLK',
            'GPRS_STATE_CSQ',
            'GPRS_STATE_CSTT',
            'GPRS_STATE_DELAY',
            'GPRS_STATE_DISABLE_GPS',
            'GPRS_STATE_FOO',
            'GPRS_STATE_INITIAL',
            'GPRS_STATE_IP_STATUS',
            'GPRS_STATE_IPSHUT',
            'GPRS_STATE_IPSPRT',
            'GPRS_STATE_KEEPALIVE',
            'GPRS_STATE_MEE',
            'GPRS_STATE_MQTTCONNECT',
            'GPRS_STATE_POWERING_UP',
            'GPRS_STATE_PUBLISH',
            'GPRS_STATE_REGISTERED',
            'GPRS_STATE_SECOND_AT')
        self.state_string_to_int_dict = {s: idx for idx, s in enumerate(self.state_string_list)}
        self.previous_state = self.state_string_to_int_dict['GPRS_STATE_INITIAL']
        self.state = self.state_string_to_int_dict['GPRS_STATE_INITIAL']
        self.next_state = self.state_string_to_int_dict['GPRS_STATE_FOO']
        self.start_delay_time = 0
        self.delay_time = 0


        self.state_list = [None]*len(self.state_string_to_int_dict)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_INITIAL']]     = GprsState(self, b'AT',           [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_DISABLE_GPS'], prefix='power_up')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_POWERING_UP']] = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_POWERING_UP'], prefix='pu_delay')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_DISABLE_GPS']] = GprsState(self, b'AT+CGNSTST=0', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_SECOND_AT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_SECOND_AT']]   = GprsState(self, b'AT',           [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_MEE'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MEE']]         = GprsState(self, b'AT+CMEE=1',    [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IPSPRT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IPSPRT']]      = GprsState(self, b'AT+CIPSPRT=0', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CALL_READY'], suffix='clear_cr')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CALL_READY']]  = GprsState(self, b'AT+CCALR?',    [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_CALR, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CALL_READY'], prefix='loop_cr')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_REGISTERED']]  = GprsState(self, b'AT+CREG?',  [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_REG, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_REGISTERED'], prefix='loop_reg', delay=2)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CLK']]         = GprsState(self, b'AT+CCLK?',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_TIME, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CSQ'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CSQ']]         = GprsState(self, b'AT+CSQ',       [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SQ, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CSQ'], prefix='loop_sq')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IPSHUT']]      = GprsState(self, b'AT+CIPSHUT',   [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SHUTOK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']]   = GprsState(self, b'AT+CIPSTATUS', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_IPSTATUS], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CSTT']]        = GprsState(self, b'AT+CSTT="m2mglobal"', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIICR']]       = GprsState(self, b'AT+CIICR',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIFSR']]       = GprsState(self, b'AT+CIFSR',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_IPADDR], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'], delay=5)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIPSTART']]    = GprsState(self, b'AT+CIPSTART="TCP","io.adafruit.com","1883"', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_CONNECTOK], self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT']] = GprsState(self, b'AT+CIPSEND',   [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SENDOK, GPRS_RESPONSE_CONNACK], self.state_string_to_int_dict['GPRS_STATE_PUBLISH'], prefix='build_connect_packet')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_PUBLISH']]     = GprsState(self, b'AT+CSQ',       [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SQ, GPRS_RESPONSE_BLANK, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_PUBLISH'], prefix='keep_alive')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_KEEPALIVE']]   = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='publish_sq')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_FOO']]         = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='state_foo')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_DELAY']]       = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='state_delay')
        #self.state_list[GPRS_STATE_xxx]        = GprsState(self, b'AT+xxx', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], GPRS_STATE_xxx)
        #set GPIO numbering mode for the program
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        RPi.GPIO.setwarnings(False)
        RPi.GPIO.setup(7, RPi.GPIO.IN)
        RPi.GPIO.setup(31, RPi.GPIO.OUT)

    def check_input(self):
        """
        read bytes from serial port concatenating them into an internal tuple of bytes
        more docstring stuff
        """
        if None != self.ser and 0 < self.ser.in_waiting:
            self.ser.timeout = 1
            newbytes = self.ser.read_until(terminator=b'\r\n')
            self.bytes += newbytes

    def stringify_response(self, token):
        """
        convert constants to string representations
        """
        if GPRS_RESPONSE_BLANK == token:
            return 'blank'
        elif GPRS_RESPONSE_OK == token:
            return 'OK'
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
        elif GPRS_RESPONSE_CONNECTOK == token:
            return 'GPRS_RESPONSE_CONNECTOK'
        elif GPRS_RESPONSE_MQTT == token:
            return 'GPRS_RESPONSE_MQTT'
        else:
            raise NotImplementedError

    # see if the string parameter is at the beginning of the recieved bytes from the radio
    def is_prefix(self, string, *, pop=False):
        if string == self.bytes[0:len(string)]:
            if pop:
                self.bytes = self.bytes[len(string):]
            return True
        else:
            #logging.debug('%s is not a prefix of %s', string, self.bytes)
            return False

    # see if the radio responded with the expected response
    def match_response(self, string, response, *, partial=False):
        if self.is_prefix(string, pop=True):
            if partial:
                pos = self.bytes.find(b'\r\n')
                #logging.debug('%s End of line is at %d', self.bytes, pos)
                if -1 == pos:
                    self.remainder = self.bytes[0:]
                    self.bytes = []
                else:
                    self.remainder = self.bytes[0:pos]
                    self.bytes = self.bytes[pos+2:]

            # match with the expected response
            if GPRS_RESPONSE_SPONTANEOUS == response:
                # don't match this with expected responses
                return True
            else:
                str_response = self.stringify_response(response)
                #logging.debug('Gprs.match_response(): found %s line', str_response)
                if 0 < len(self.response_list):
                    if response == self.response_list[0]:
                        #logging.debug('remove %s from response_list', str_response)
                        self.response_list.pop(0)
                        return True
                    else:
                        logging.error('Gprs.match_response(): found %s line where %s was expected', str_response, self.stringify_response(self.response_list[0]))
                        # What do we do now?
                        self.previous_state = self.state
                        self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']

                else:
                    # got a blank line while not expecting any response
                    logging.error('Gprs.match_response(): found blank line where nothing was expected')
                    self.previous_state = self.state
                    self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']

        return False

    # remove bytes until we reach \r\n
    def clear_to_end_of_line(self):
        pos = self.bytes.find(b'\r\n')
        #logging.debug('%s End of line is at %d', self.bytes, pos)
        if -1 == pos:
            raise NotImplementedError
        self.bytes = self.bytes[pos+2:]

    # match bytes from the radio with expected responses
    def process_bytes(self):
        # if there is no response from radio, just return
        numbytes = len(self.bytes)
        if 0 == numbytes:
            return False

        # handle responses that do not end with \r\n (tyically MQTT packets)
        if 0 < len(self.response_list) and GPRS_RESPONSE_CONNACK == self.response_list[0]:
            if 4 <= numbytes:
                # MQTT CONNACK packet
                # opcode 32
                # length - 2
                # session present - 0 or 1
                # payload - 0, 1, 2, 3, 4, 5
                #if (b' ' == self.bytes[0]
                #and b'\x02' == self.bytes[1]
                #and (b'\x00' == self.bytes[2] or b'\x01' == self.bytes[2])):
                if (32 == self.bytes[0]
                and 2 == self.bytes[1]
                and (0 == self.bytes[2] or 1 == self.bytes[2])):
                    if 0 == self.bytes[3]:
                        logging.info('Got CONNACK from MQTT broker.  Connected is now true.')
                        self.response_list.pop(0)
                        self.bytes = self.bytes[4:]
                        self.connected = True
                        return True
                    else:
                        logging.error('CONNACK connection refused.  Status %s', self.bytes[3])
                        self.previous_state = self.state
                        self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']

        elif 0 < len(self.response_list) and GPRS_RESPONSE_MQTT == self.response_list[0]:
            if (48 == self.bytes[0] # MQTT_CTRL_PUBLISH<<4
            and 3+self.bytes[1] <= len(self.bytes)): # length matches
                self.bytes = self.bytes[3+self.bytes[1]:]
                self.response_list.pop(0)
                return True

        if not b'\r\n' in self.bytes:
            logging.debug('partial line detected %d %s', numbytes, self.bytes)
            return False

        # try to match the response (we could refactor relative to self.command)
        logging.debug('    Gprs.process_bytes() %s - %s %s', self.lines_of_response, self.bytes, self.response_list)
        self.lines_of_response += 1
        if self.match_response(b'\r\n', GPRS_RESPONSE_BLANK):
            pass
        elif self.is_prefix(b'AT+', pop=False):
            if self.match_response(self.command + b'\r\r\n', GPRS_RESPONSE_ECHO):
                pass
            elif self.match_response('AT+CIPSEND\r\n', GPRS_RESPONSE_ECHO):
                # Sometimes, we get the mqtt packet after echo
                if (0 == len(self.response_list)
                and self.state_string_to_int_dict['GPRS_STATE_PUBLISH'] == self.previous_state): # we have advanced to the next state already
                    self.response_list = [GPRS_RESPONSE_MQTT]
                else:
                    logging.error('AT+CIPSEND\\r\\n seen while response list was not empty (%s)', self.response_list)
                    self.previous_state = self.state
                    self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']
            elif self.match_response(self.command + b'\r', GPRS_RESPONSE_ECHO, partial=True):
                # self.remainder should be the remainder of the line (e.g. MQTT connect packet)
                pass
            else:
                logging.error('got AT+ prefix but not %s\\r\\r\\n', self.command)
                return False
        elif self.is_prefix(b'AT', pop=False):
            if self.match_response(b'AT\r\r\n', GPRS_RESPONSE_ECHO):
                pass
            else:
                logging.error('AT prefix, but not AT\\r\\r\\n')
                return False
        elif self.match_response(b'OK\r\n', GPRS_RESPONSE_OK):
            pass
        elif self.match_response(b'SHUT OK\r\n', GPRS_RESPONSE_SHUTOK):
            pass
        elif self.match_response(b'SEND OK\r\n', GPRS_RESPONSE_SENDOK):
            pass
        elif self.match_response(b'STATE: IP INITIAL\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_CSTT']
        elif self.match_response(b'STATE: IP START\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_CIICR']
        elif self.match_response(b'STATE: IP GPRSACT\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_CIFSR']
        elif self.match_response(b'STATE: IP STATUS\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_CIPSTART']
        elif self.match_response(b'STATE: TCP CLOSED\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IPSHUT']
            pass
        elif self.match_response(b'STATE: IP CONFIG\r\n', GPRS_RESPONSE_IPSTATUS):
            logging.debug('Delay 3 seconds before going into state GPRS_STATE_IP_STATUS')
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_DELAY']
            self.start_delay_time = time.time()
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.delay_time = 3
        elif self.match_response(b'STATE: TCP CONNECTING\r\n', GPRS_RESPONSE_IPSTATUS):
            logging.debug('Delay 10 seconds before going into state GPRS_STATE_IP_STATUS')
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_DELAY']
            self.start_delay_time = time.time()
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.delay_time = 10
        elif self.match_response(b'STATE: TCP CLOSING\r\n', GPRS_RESPONSE_IPSTATUS):
            logging.debug('Delay 3 seconds before going into state GPRS_STATE_IP_STATUS')
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_DELAY']
            self.start_delay_time = time.time()
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.delay_time = 3
        elif self.match_response(b'STATE: PDP DEACT\r\n', GPRS_RESPONSE_IPSTATUS):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IPSHUT']
        elif self.match_response(b'CONNECT OK\r\n', GPRS_RESPONSE_CONNECTOK):
            pass
        elif self.match_response(b'+CCALR: 0\r\n', GPRS_RESPONSE_CALR):
            self.call_ready = False
        elif self.match_response(b'+CCALR: 1\r\n', GPRS_RESPONSE_CALR):
            self.call_ready = True
        elif self.match_response(b'+CREG: 0,0\r\n', GPRS_RESPONSE_REG):
            self.registered = False
        elif self.match_response(b'+CREG: 0,1\r\n', GPRS_RESPONSE_REG):
            self.registered = True
        elif self.match_response(b'+CREG: 0,2\r\n', GPRS_RESPONSE_REG):
            self.registered = False
        elif self.match_response(b'+CREG: 0,5\r\n', GPRS_RESPONSE_REG): # roaming
            self.registered = True

        elif self.match_response(b'+CCLK: "', GPRS_RESPONSE_TIME, partial=True):
            temp = self.remainder.decode(encoding='UTF-8').split(',') # yy/MM/dd,hh:mm:ss+zz"
            # temp[0] is yy/MM/dd
            # temp[1] is hh:mm:ss+zz"
            logging.debug('Time is %s', temp[1][0:-1])

        elif self.match_response(b'+CSQ: ', GPRS_RESPONSE_SQ, partial=True):
            temp = self.remainder.decode(encoding='UTF-8').split(',')
            signal = temp[0]
            if 1 == len(signal):
                self.signal = ord(signal[0]) - ord(b'0')
            elif 2 == len(signal):
                self.signal = (ord(signal[0]) - ord(b'0'))*10 + (ord(signal[1]) - ord(b'0'))
            else:
                logging.error('This is unexpected.  len(signal) is %s', len(signal))
                self.signal = 0
            logging.debug('Signal quality is %d', self.signal)

        # Error conditions
        elif self.match_response(b'+PDP: DEACT\r\n', GPRS_RESPONSE_SPONTANEOUS):
            logging.info("Got PDP: DEACT %s %s", self.response_list, self.state_string_list[self.previous_state])
            if (1 == len(self.response_list)
            and GPRS_RESPONSE_OK == self.response_list[0]
            and self.state_string_to_int_dict['GPRS_STATE_CIICR'] == self.previous_state): # we have advanced to the next state already
                self.response_list = [GPRS_RESPONSE_BLANK, GPRS_RESPONSE_ERROR]
        elif self.match_response(b'ERROR\r\n', GPRS_RESPONSE_ERROR):
            pass
        elif self.match_response(b'CLOSED\r\n', GPRS_RESPONSE_SPONTANEOUS):
            self.connected = False
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']
        elif self.match_response(b'CONNECT FAIL\r\n', GPRS_RESPONSE_SPONTANEOUS):
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']

        # hard to identify things (need regex or some such)
        elif 0 < len(self.response_list) and GPRS_RESPONSE_IPADDR == self.response_list[0]:
            temp = self.bytes.decode(encoding='UTF-8').split('.') # xxx.xxx.xxx.xxx
            if 4 == len(temp):
                logging.debug('IP Address is %s.%s.%s.%s', temp[0], temp[1], temp[2], temp[3])
                self.response_list.pop(0)
                self.clear_to_end_of_line()
            else:
                logging.error('Failed to parse line that should have been an IP address: %s', self.bytes)
                self.previous_state = self.state
                self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']

        else:
            logging.error('Gprs.process_bytes(): write code to handle %s %d', self.bytes, numbytes)
            raise NotImplementedError
            #self.clear_to_end_of_line()
            return False

        return True

    def loop(self):
        #logging.debug('loop')
        self.loop_time = time.time()
        self.check_input()
        while self.process_bytes(): # this needs a timeout or iteration limit
            if 0 == len(self.response_list):
                # we have satisfied the expected response for the command
                logging.info('%s done in %d seconds. Next state %s. Radio is now idle.', self.command, self.loop_time-self.command_start_time, self.state_string_list[self.next_state])
                self.radio_busy = False
                self.previous_state = self.state
                self.state = self.next_state
                self.packet = ()

        if self.radio_busy:
            if self.state_string_to_int_dict['GPRS_STATE_FOO'] == self.state:
                self.state_list[self.state].run()
            else:
                # wait for radio to finish current operation
                pass

        else:
            # Here is where we execute the state machine that controls connecting
            # the radio to the AdaFruit MQTT broker
            #logging.debug('about to step the machine')
            try:
                self.state_list[self.state].run()

            except xxx as e:
                logging.info('xxx exception %s', e, exc_info=True, stack_info=True)
            except Exception as e:
                logging.error('Exception: %s', e)
            else:
                pass

    def int_to_bytes(self, value):
        result = b''
        while (value > 0):
            result = (chr(48+(value%10))).encode(encoding='UTF-8')+result
            value = value/10
        return result

    def build_connect_packet(self):
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
        packet += hostname.encode(encoding='UTF-8')
        # Will Topic
        # Will Message
        # Username
        packet.append(0x00) # username length MSB
        packet.append(len(username)) # username length LSB
        packet += username.encode(encoding='UTF-8')
        # Password
        packet.append(0x00) # password length MSB
        packet.append(len(password)) # password length LSB
        packet += password.encode(encoding='UTF-8')
        # Fill in packet length
        if 127 < len(packet)-2:
            logging.error('Write more code 3')
            raise NotImplementedError
        if 28 == len(packet):
            logging.error('Write more code 4')
            raise NotImplementedError
        if 29 == len(packet):
            logging.error('Write more code 5')
            raise NotImplementedError
        packet[1] = len(packet)-2
        # GPRS MODEM end of transmission flag
        packet.append(26) # not really part of the packet
        return packet

    def build_message_packet(self, topic, message):
        # publish packet
        packet = bytearray(0)
        packet.append(0x30) # MQTT_CTRL_PUBLISH << 4
        packet.append(0) # length for now is zero
        # Topic name
        fulltopic = b''
        fulltopic += username.encode(encoding='UTF-8')
        fulltopic += b'/feeds/'
        fulltopic += topic.encode(encoding='UTF-8')
        packet.append(0) # length for topic name MSB
        packet.append(len(fulltopic)) # length for topic name LSB
        packet += fulltopic
        # payload
        # no length encoded here
        packet += ascii(message).encode(encoding='UTF-8')
        # avoid "bad" length packets (28 and 29 are "bad")
        if 28 == len(packet):
            packet += b'  '
        if 29 == len(packet):
            packet += b' '
        packet[1] = len(packet)-2 # fill in the length
        packet.append(26) # not really part of the packet

        return packet

    def send_command(self, command, bytes, response_list, next_state):
        logging.debug('Gprs.send_command(): Sending command %s', command)
        self.command = command
        self.response_list = response_list
        self.next_state = next_state
        self.radio_busy = True
        self.command_start_time = time.time()
        self.lines_of_response = 0
        self.ser.write(command)
        self.ser.write(b'\r\n')
        if len(bytes):
            logging.debug('Sending additional bytes')
            time.sleep(0.5)
            self.ser.write(bytes)

    def is_ready(self):
        #logging.debug('is_ready() %s %s', self.connected, self.radio_busy)
        return self.connected and not self.radio_busy

    def publish(self, topic, message):
        logging.debug('Gprs.publish() to %s', topic)
        if self.radio_busy:
            raise NotImplementedError
        if not self.connected:
            raise NotImplementedError
        packet = self.build_message_packet(topic, message)
        self.send_command(b'AT+CIPSEND', packet, [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SENDOK], self.state_string_to_int_dict['GPRS_STATE_PUBLISH'])

