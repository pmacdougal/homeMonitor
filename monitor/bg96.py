import logging
import serial
import time
import RPi.GPIO
from socket import gethostname
from .private import username, password

'''
Code to handle a Quectel BG96 LTE radio chip
https://sixfab.com/product/raspberry-pi-lte-m-nb-iot-egprs-cellular-hat
Raspberry Pi Cellular IoT HAT – LTE-M & NB-IoT & eGPRS

ToDo:
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
GPRS_RESPONSE_FLUSH = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_CONNECTFAIL = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_QMTCLOSE = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_QMTOPEN = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_QMTCONN = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_QMTPUB = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1
GPRS_RESPONSE_PACKET = GPRS_RESPONSE_MAX; GPRS_RESPONSE_MAX += 1

class xxx(Exception):
    pass

class GprsState:
    '''
    State Machine State with actions to perform and next state to transition to
    '''
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
        '''
        do nothing but return 0
        '''
        return 0

    def method_return_one(self):
        '''
        do nothing but return 1
        '''
        return 1

    def method_ccr(self):
        '''
        clear call ready in the radio
        '''
        self.radio.call_ready = False
        self.loop_count = 0
        return 0

    def method_cr_loop(self):
        '''
        if radio is ready to make a call, return 1
        '''
        self.loop_count += 1
        if self.radio.call_ready:
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_REGISTERED']
            self.radio.registered = False
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning('method_cr_loop() stuck in loop')
            self.radio.goto_foo()
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_cr_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_reg_loop(self):
        '''
        if radio is registered on the network, return 1
        '''
        self.loop_count += 1
        if self.radio.registered:
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_CSQ']
            self.radio.signal = 0
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning('method_reg_loop() stuck in loop')
            self.radio.goto_foo()
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_reg_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_sq_loop(self):
        '''
        if radio has sufficient signal strength, return 1
        '''
        self.loop_count += 1
        if 4 < self.radio.signal:
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_MQTTOPEN']
            self.loop_count = 0
            return 1
        elif False and 20 == self.loop_count:
            logging.warning('method_sq_loop() stuck in loop')
            self.radio.goto_foo()
            return 1
        elif 1 < self.loop_count:
            logging.debug('method_sq_loop() count %d', self.loop_count)
            time.sleep(1)
        return 0

    def method_build_connect_packet(self):
        '''
        build a MQTT connect packet
        '''
        self.packet = self.radio.build_connect_packet()
        return 0

    def method_keep_alive(self):
        '''
        periodically, the radio needs to communicate with AdaFruit
        We publish the radio signal quality if nothing else is going on
        '''
        delta = self.radio.loop_time - self.radio.command_start_time
        #logging.info('Keep_alive %d', delta)
        if 240 < delta:
            return 0
        return 1

    def method_publish_sq(self):
        '''
        publish radio strength
        always returns 1, so that we do not do a radio.send_command
        '''
        if self.radio.is_ready():
            self.radio.publish('s.sq', self.radio.signal)
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.next_state
        else:
            logging.info('method_publish_sq(): Radio is not ready')
        return 1

    def method_foo(self):
        '''
        handle errors
        '''
        logging.info('method_foo(): STATE_FOO entered with state machine coming from %s', self.radio.state_string_list[self.radio.previous_state])
        # loop here for a while, dumping radio output
        start = time.time()
        while 30 > (time.time() - start): # 30 seconds
            if self.radio.check_radio_output():
                print(self.radio.radio_output)
                self.radio.radio_output = b''
            time.sleep(0.5)
        raise KeyboardInterrupt # try to exit the program here

    def method_power_up(self):
        '''
        check if the radio is powered on
        open the serial port
        '''
        if RPi.GPIO.input(self.radio.STATUS):
            # Pull the power pin high for three seconds
            RPi.GPIO.output(self.radio.BG96_POWERKEY, RPi.GPIO.HIGH)
            logging.info('The radio is OFF.  Pulling pwrkey high... ')
            self.radio.start_time = self.radio.loop_time
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_POWERING_UP']
            return 1
        else:
            logging.info('The radio is ON.  Opening serial port. ')
            # Open the serial port
            self.radio.ser = serial.Serial(self.radio.port, 115200)
            if None == self.radio.ser:
                logging.error('Unable to open serial port %s', self.radio.port)
                return 1
        return 0

    def method_power_up_delay(self):
        '''
        release power button after 3 seconds
        always returns 1, so that we do not do a radio.send_command
        '''
        if 3 <= (self.radio.loop_time - self.radio.start_time):
            RPi.GPIO.output(self.radio.BG96_POWERKEY, RPi.GPIO.LOW)
            logging.info('Releasing pwrkey')
            self.radio.previous_state = self.radio.state
            self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_INITIAL']
        return 1

    def method_delay(self):
        '''
        delay before going to next state
        always returns 1, so that we do not do a radio.send_command
        '''
        if self.radio.delay_duration <= (self.radio.loop_time - self.radio.start_delay_time):
            logging.debug('Advance to %s', self.radio.state_string_list[self.radio.next_state])
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
        if ('GPRS_STATE_PUBLISH' != self.radio.state_string_list[self.radio.state]
        and 'GPRS_STATE_POWERING_UP' != self.radio.state_string_list[self.radio.state]):
            logging.info('### %s %s %s', self.radio.state_string_list[self.radio.state], self.prefix, self.suffix)
        ret1 = self.METHODS[self.prefix](self)
        ret2 = 0
        if 0 == ret1:
            # make a copy of the response list in case we re-visit this state
            self.radio.send_command(self.command_string, self.packet, self.response_list.copy(), self.next_state)
            ret2 = self.METHODS[self.suffix](self)
            if 0 < self.delay:
                logging.debug('Delay %d seconds before going into state %s', self.delay, self.radio.state_string_list[self.next_state])
                self.radio.previous_state = self.radio.state
                self.radio.state = self.radio.state_string_to_int_dict['GPRS_STATE_DELAY']
                self.radio.start_delay_time = time.time()
                self.radio.next_state = self.next_state
                self.radio.delay_duration = self.delay
            else:
                self.radio.previous_state = self.radio.state
                self.radio.state = self.next_state
        return ret1, ret2


class Bg96:
    '''
    Class for Raspberry Pi Cellular IoT HAT – LTE-M & NB-IoT & eGPRS
    '''
    # Broadcom Pin numbering
    #USER_BUTTON = 22
    #USER_LED = 27
    #BG96_ENABLE = 17
    #BG96_POWERKEY = 24
    #STATUS = 23

    # Board Pin numbering
    USER_BUTTON = 15
    USER_LED = 13
    BG96_ENABLE = 11
    BG96_POWERKEY = 18
    STATUS = 16

    def __init__(self, port):
        logging.debug('Constructing Bg96 object')
        self.port = port
        self.radio_busy = False
        self.ser = None
        #self.bytes = b''
        self.radio_output = b''
        self.response_list = []
        self.command = b''
        self.command_start_time = 0
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
            'GPRS_STATE_FLUSH',
            'GPRS_STATE_FOO',
            'GPRS_STATE_INITIAL',
            'GPRS_STATE_IP_STATUS',
            'GPRS_STATE_IPSHUT',
            'GPRS_STATE_IPSPRT',
            'GPRS_STATE_KEEPALIVE',
            'GPRS_STATE_MEE',
            'GPRS_STATE_MQTTCONNECT',
            'GPRS_STATE_MQTTOPEN',
            'GPRS_STATE_MQTTSHUT',
            'GPRS_STATE_POWERING_UP',
            'GPRS_STATE_PUBLISH',
            'GPRS_STATE_REGISTERED',
            'GPRS_STATE_SECOND_AT',
            'GPRS_STATE_UNDEFINED')
        self.state_string_to_int_dict = {s: idx for idx, s in enumerate(self.state_string_list)}
        self.previous_state = self.state_string_to_int_dict['GPRS_STATE_INITIAL']
        self.state = self.state_string_to_int_dict['GPRS_STATE_INITIAL']
        self.next_state = self.state_string_to_int_dict['GPRS_STATE_UNDEFINED']
        self.start_delay_time = 0
        self.delay_duration = 0
        self.successfully_published = False
        self.output_timeout_start_time = 0
        self.lasttopic = ""

        self.state_list = [None]*len(self.state_string_to_int_dict)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_INITIAL']]     = GprsState(self, b'AT',           [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_REGISTERED'], prefix='power_up')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_POWERING_UP']] = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_POWERING_UP'], prefix='pu_delay')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_REGISTERED']]  = GprsState(self, b'AT+CREG?',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_REG, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_REGISTERED'], prefix='loop_reg', delay=2)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CSQ']]         = GprsState(self, b'AT+CSQ',       [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SQ, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CSQ'], prefix='loop_sq')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MQTTSHUT']]    = GprsState(self, b'AT+QMTCLOSE=1',[GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_QMTCLOSE], self.state_string_to_int_dict['GPRS_STATE_MQTTOPEN'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MQTTOPEN']]    = GprsState(self, b'AT+QMTOPEN=1,"io.adafruit.com",1883',   [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_QMTOPEN], self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT']] = GprsState(self, b'AT+QMTCONN=1,"bg96","'+username.encode(encoding='UTF-8')+b'","'+password.encode(encoding='UTF-8')+b'"',   [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_QMTCONN], self.state_string_to_int_dict['GPRS_STATE_PUBLISH'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_PUBLISH']]     = GprsState(self, b'AT+CSQ',       [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SQ, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_KEEPALIVE'], prefix='keep_alive')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_KEEPALIVE']]   = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='publish_sq')





        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CALL_READY']]  = GprsState(self, b'AT+CCALR?',    [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_CALR, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CALL_READY'], prefix='loop_cr')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIFSR']]       = GprsState(self, b'AT+CIFSR',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_IPADDR], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'], delay=5)
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIICR']]       = GprsState(self, b'AT+CIICR',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CIPSTART']]    = GprsState(self, b'AT+CIPSTART="TCP","io.adafruit.com","1883"', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_CONNECTOK], self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CLK']]         = GprsState(self, b'AT+CCLK?',     [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_TIME, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CSQ'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_CSTT']]        = GprsState(self, b'AT+CSTT="m2mglobal"', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_DELAY']]       = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='state_delay')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_DISABLE_GPS']] = GprsState(self, b'AT+CGNSTST=0', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_SECOND_AT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_FLUSH']]       = GprsState(self, b'AT',           [GPRS_RESPONSE_FLUSH, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_FOO']]         = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'], prefix='state_foo')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']]   = GprsState(self, b'AT+CIPSTATUS', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK, GPRS_RESPONSE_IPSTATUS], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IPSHUT']]      = GprsState(self, b'AT+CIPSHUT',   [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_SHUTOK], self.state_string_to_int_dict['GPRS_STATE_IP_STATUS'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_IPSPRT']]      = GprsState(self, b'AT+CIPSPRT=0', [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_CALL_READY'], suffix='clear_cr')
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_MEE']]         = GprsState(self, b'AT+CMEE=1',    [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IPSPRT'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_SECOND_AT']]   = GprsState(self, b'AT',           [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_MEE'])
        self.state_list[self.state_string_to_int_dict['GPRS_STATE_UNDEFINED']]   = GprsState(self, b'',             [], self.state_string_to_int_dict['GPRS_STATE_FOO'])
        #self.state_list[self.state_string_to_int_dict[GPRS_STATE_xxx]]          = GprsState(self, b'AT+xxx',       [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_OK], self.state_string_to_int_dict['GPRS_STATE_IP_xxx'])

        #set GPIO numbering mode for the program
        RPi.GPIO.setmode(RPi.GPIO.BOARD)
        RPi.GPIO.setwarnings(False)
        RPi.GPIO.setup(self.BG96_ENABLE, RPi.GPIO.OUT)
        RPi.GPIO.setup(self.BG96_POWERKEY, RPi.GPIO.OUT)
        RPi.GPIO.setup(self.STATUS, RPi.GPIO.IN)
        RPi.GPIO.setup(self.USER_BUTTON, RPi.GPIO.IN)
        RPi.GPIO.setup(self.USER_LED, RPi.GPIO.OUT)

    def __del__(self):
        RPi.GPIO.cleanup()


    def check_radio_output(self):
        '''
        read bytes from serial port concatenating them into an internal bytes array
        more docstring stuff
        '''
        if None != self.ser and 0 < self.ser.in_waiting:
            self.ser.timeout = 1
            newbytes = self.ser.read_until(terminator=b'\r\n')
            self.radio_output += newbytes
            # should keep the last N values of newbytes for debugging here
            self.output_timeout_start_time = time.time()
            return len(newbytes)

        # timeout
        if self.radio_busy and 120 < time.time() - self.output_timeout_start_time:
            logging.warn("It has been two minutes since we got radio output")
            self.output_timeout_start_time = time.time() # reset
        return 0

    def goto_foo(self):
        '''
        Cause the state machine to enter the 'Something bad has happened' state
        '''
        if 0 == len(self.response_list):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_FOO']
        else:
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_FOO']
            self.next_state = self.state

    def handle_radio_output(self):
        '''
        Collect serial output from the radio and see if it matches the expected response
        returns True if it consumes some of the radio output
        '''
        bytelength = len(self.radio_output)
        # if we have no chars from the radio, attempt to read some
        if 0 == bytelength:
            self.check_radio_output()
            return False

        crlf = self.radio_output.find(b'\r\n')
        if -1 == crlf:
            # We have bytes, but not a CRLF
            # This happens when we are waiting for a MQTT response
            # It also happens when we timeout on reading from radio (partial response)
            if 0 < len(self.response_list) and GPRS_RESPONSE_CONNACK == self.response_list[0]:
                if 4 <= bytelength:
                    # MQTT CONNACK packet
                    # opcode 32
                    # length - 2
                    # session present - 0 or 1
                    # payload - 0, 1, 2, 3, 4, 5
                    if (32 == self.radio_output[0]
                    and 2 == self.radio_output[1]
                    and (0 == self.radio_output[2] or 1 == self.radio_output[2])):
                        if 0 == self.radio_output[3]:
                            logging.info('Got CONNACK from MQTT broker.  Connected is now true.')
                            self.connected = True
                        else:
                            logging.error('CONNACK connection refused.  Status %s', self.radio_output[3])
                            self.connected = False
                            # Try to connect again
                            self.next_state = self.state_string_to_int_dict['GPRS_STATE_MQTTCONNECT']
                        self.radio_output = self.radio_output[4:]
                        self.response_list.pop(0)
                        return True

                    else:
                        logging.error('Bg96.handle_radio_output() was expecting a CONNACK packet')
                        self.goto_foo()
                        return False
                else:
                    # try to read more bytes
                    self.check_radio_output()
                    return False

            elif 0 < len(self.response_list) and GPRS_RESPONSE_MQTT == self.response_list[0]:
                if 4 <= bytelength:
                    # MQTT PUBLISH packet (we just built this, the radio echoes it back)
                    # opcode 48
                    # length - ??
                    if (48 == self.radio_output[0] # MQTT_CTRL_PUBLISH<<4
                    and 3+self.radio_output[1] <= len(self.radio_output)): # length matches
                        self.radio_output = self.radio_output[3+self.radio_output[1]:]
                        self.response_list.pop(0)
                        return True
                    else:
                        logging.error('Bg96.handle_radio_output() was expecting a CONNACK packet')
                        self.goto_foo()
                        return False
                else:
                    # try to read more bytes
                    self.check_radio_output()
                    return False
            else:
                self.check_radio_output()
                return False

        elif crlf == bytelength-2: # self.radio_output has a CRLF at the end of the string
            return self.handle_line(self.radio_output)

        else: # self.radio_output has a CRLF before the end of the string)
            # every once in a while, we end up with two lines from the radio
            # e.g. b'AT+CIICR\r\r\nOK\r\n'
            # separate out the first line
            firstline = self.radio_output[0:crlf+2]
            return self.handle_line(firstline)

        return False # not sure we can get here

    def handle_line(self, line):
        logging.debug('    Bg96.handle_radio_output() %s - %s %s', self.lines_of_response, self.radio_output, self.response_list)
        self.lines_of_response += 1
        if (100 < self.lines_of_response): # anything over 4 or 5 lines is 'stuck'
            logging.error('We are stuck.')
            self.goto_foo()
            return False

        # see if we are in the FLUSH state
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_FLUSH == self.response_list[0]):
                self.response_matches()
                return True
        # See if this is exactly one of the expected responses (e.g. 'OK\r\n')
        elif line in self.METHODS:
            method = self.METHODS[line]
            return method['method'](self, method['arg'])
        # Other parsing of radio output
        else:
            # do regex stuff here
            if (line.startswith(b'AT+QMTPUB=1,0,0,0,')
            and 0 < len(self.response_list)
            and GPRS_RESPONSE_ECHO == self.response_list[0]):
                # remainder of the line is the MQTT packet we sent.  No need to parse it
                self.response_matches()
                return True
            elif (line.startswith(b'>')
            and 0 < len(self.response_list)
            and GPRS_RESPONSE_PACKET == self.response_list[0]):
                self.response_matches()
                return True
            elif (line.startswith(b'AT+CIPSEND\r')
            and 0 < len(self.response_list)
            and GPRS_RESPONSE_ECHO == self.response_list[0]):
                # remainder of the line is the MQTT packet we sent.  No need to parse it
                self.response_matches()
                return True
            elif (line.startswith(b'+CCLK: "')
            and 0 < len(self.response_list)
            and GPRS_RESPONSE_TIME == self.response_list[0]):
                temp = line[8:].decode(encoding='UTF-8').split(',') # yy/MM/dd,hh:mm:ss+zz"
                # temp[0] is yy/MM/dd
                # temp[1] is hh:mm:ss+zz"
                logging.debug('Time is %s', temp[1][0:-4])
                self.response_matches()
                return True
            elif (line.startswith(b'+CSQ: ')
            and 0 < len(self.response_list)
            and GPRS_RESPONSE_SQ == self.response_list[0]):
                temp = line[6:].decode(encoding='UTF-8').split(',')
                signal = temp[0]
                if 1 == len(signal):
                    self.signal = ord(signal[0]) - ord(b'0')
                elif 2 == len(signal):
                    self.signal = (ord(signal[0]) - ord(b'0'))*10 + (ord(signal[1]) - ord(b'0'))
                else:
                    logging.error('This is unexpected.  len(signal) is %s', len(signal))
                    self.signal = 0
                logging.debug('Signal quality is %d', self.signal)
                self.response_matches()
                return True
            elif line.startswith(b'+CME ERROR: '):
                errno = int(line[11:].decode(encoding='UTF-8'))
                return self.method_match_cme_error(errno)
            elif (0 < len(self.response_list)
            and GPRS_RESPONSE_IPADDR == self.response_list[0]):
                temp = line.decode(encoding='UTF-8').split('.') # xxx.xxx.xxx.xxx
                if 4 == len(temp):
                    logging.debug('IP Address is %s.%s.%s.%s', temp[0], temp[1], temp[2], temp[3])
                    self.response_matches()
                    return True
                else:
                    logging.error('Failed to parse line that should have been an IP address: %s', line)
                    self.goto_foo()
                    return False
            else:
                logging.error('radio output not parsed: %s', line)
                self.goto_foo()
                return False

        return False # not sure we can get here

    def loop(self):
        '''
        routine to handle the radio
        '''
        #logging.debug('loop')
        self.loop_time = time.time()

        if True:
            while self.handle_radio_output(): # this needs a timeout or iteration limit
                if (self.radio_busy
                and 0 == len(self.response_list)):
                    # we have satisfied the expected response for the command
                    logging.info('%s done in %d seconds. Next state %s. Radio is now idle.', self.command, self.loop_time-self.command_start_time, self.state_string_list[self.next_state])
                    self.radio_busy = False
                    self.previous_state = self.state
                    self.state = self.next_state
                    self.next_state = self.state_string_to_int_dict['GPRS_STATE_UNDEFINED']
                    self.packet = ()
        '''
        else:
            newbytes = self.check_input()
            while self.process_bytes(newbytes): # this needs a timeout or iteration limit
                if 0 == len(self.response_list):
                    # we have satisfied the expected response for the command
                    logging.info('%s done in %d seconds. Next state %s. Radio is now idle.', self.command, self.loop_time-self.command_start_time, self.state_string_list[self.next_state])
                    self.radio_busy = False
                    self.previous_state = self.state
                    self.state = self.next_state
                    self.packet = ()
        '''
        if (self.radio_busy
        and self.state_string_to_int_dict['GPRS_STATE_FOO'] != self.state):
            # wait for radio to finish current operation
            pass

        else:
            # Here is where we execute the state machine that controls connecting
            # the radio to the AdaFruit MQTT broker
            #logging.debug('about to step the machine in %s', self.state_string_list[self.state])
            try:
                self.state_list[self.state].run()

            except xxx as e:
                logging.info('xxx exception %s', e, exc_info=True, stack_info=True)
            except Exception as e:
                logging.error('Exception: %s', e, exc_info=True)
            else:
                pass
    '''
    def int_to_bytes(self, value):
        result = b''
        while (value > 0):
            result = (chr(48+(value%10))).encode(encoding='UTF-8')+result
            value = value/10
        return result
    '''

    def build_connect_packet(self):
        '''
        build an MQTT connect packet
        '''
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
        '''
        put the message into a CTRL-Z terminated bytearray
        '''
        # publish packet
        packet = bytearray(0)
        packet += ascii(message).encode(encoding='UTF-8')
        packet.append(26) # not really part of the packet
        return packet

    def send_command(self, command, bytes, response_list, next_state):
        '''
        Send a command to the radio (including extra bytes if needed)
        '''
        # Rate limit sending commands to the radio to avoid exceeding the data rate on my cell phone plan
        # Not all commands sent to the radio cause actual traffic to the cell phone tower, but ...
        # The penalty for exceeding the rate appears to be cancelation of your data plan.
        now = time.time()
        while 1 > now-self.command_start_time:
            time.sleep(0.5)
            now = time.time()
        self.command_start_time = now

        logging.debug('Bg96.send_command(): Sending command %s', command)
        self.command = command
        self.response_list = response_list
        self.next_state = next_state
        self.radio_busy = True
        self.output_timeout_start_time = time.time()
        self.lines_of_response = 0
        self.ser.write(command)
        self.ser.write(b'\r\n')
        if len(bytes):
            logging.debug('Sending additional bytes')
            time.sleep(0.5)
            self.ser.write(bytes)

    def is_ready(self):
        '''
        See if the radio is ready to send data to AdaFruit
        '''
        #logging.debug('is_ready() %s %s', self.connected, self.radio_busy)
        return self.connected and not self.radio_busy

    def response_matches(self):
        if 0 < len(self.response_list):
            logging.debug('response_matches() called because radio response matches the expected response %d', self.response_list[0])
            self.response_list.pop(0)
            pos = self.radio_output.find(b'\r\n')
            #logging.debug('%s End of line is at %d', self.radio_output, pos)
            if -1 == pos:
                raise NotImplementedError
            self.radio_output = self.radio_output[pos+2:]
        else:
            logging.error('response_matches() called with empty response_list')
            self.goto_foo()

    def response_mismatches(self, arg):
        if 0 < len(self.response_list):
            logging.error('response_mismatches() called because response %d does not match the expected response %d', arg, self.response_list[0])
            # don't pop the response list
            # consume the radio output
            pos = self.radio_output.find(b'\r\n')
            #logging.debug('%s End of line is at %d', self.radio_output, pos)
            if -1 == pos:
                raise NotImplementedError
            self.radio_output = self.radio_output[pos+2:]
            self.goto_foo()
        else:
            logging.error('response_mismatches() called with empty response_list')
            self.goto_foo()

    def method_match_generic(self, token):
        '''
        check if the front of the response list is 'token'
        allow tokens to match the empty list
        '''
        if (0 < len(self.response_list)
        and token == self.response_list[0]):
            self.response_matches()
            return True
        else:
            if 0 == len(self.response_list):
                self.response_list = [GPRS_RESPONSE_SPONTANEOUS]
                self.response_matches()
                return True
        self.response_mismatches(token)
        return False

    def method_match_ipstatus(self, strstate):
        '''
        check if the front of the response list is GPRS_RESPONSE_IPSTATUS
        then dispatch to the proper next state
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_IPSTATUS == self.response_list[0]):
            self.next_state = self.state_string_to_int_dict[strstate]
            self.response_matches()
            return True
        elif (0 < len(self.response_list)
        and GPRS_RESPONSE_CONNECTOK == self.response_list[0]
        and self.state_string_to_int_dict['GPRS_STATE_CIPSTART'] == self.previous_state): # we have advanced to the next state already
            # I have seen this happen a couple of times
            # expecting CONNECT OK, but get STATE: IP STATUS
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.response_list = [GPRS_RESPONSE_IPSTATUS, GPRS_RESPONSE_CONNECTFAIL]
            self.response_matches()
            return True
        self.response_mismatches(GPRS_RESPONSE_IPSTATUS)
        return False

    def method_match_ipconfig(self, delay):
        '''
        check if the front of the response list is GPRS_RESPONSE_IPSTATUS
        then delay some amount before going to state GPRS_STATE_IP_STATUS
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_IPSTATUS == self.response_list[0]):
            logging.debug('Delay %d seconds before going into state GPRS_STATE_IP_STATUS', delay)
            self.previous_state = self.state
            self.state = self.state_string_to_int_dict['GPRS_STATE_DELAY']
            self.start_delay_time = time.time()
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.delay_duration = delay
            self.response_matches()
            return True
        self.response_mismatches(GPRS_RESPONSE_IPSTATUS)
        return False

    def method_premature_ipsend(self, token):
        '''
        Usually, we get AT+CIPSEND\\r<MQTT PACKET>\\r\\n
        but, sometimes we get AT+CIPSEND\\r\\n<MQTT PACKET>
        '''
        logging.debug('Got AT+CIPSEND\\r\\n %s %s %s %s %s %s', self.response_list, self.state_string_list[self.previous_state], self.state_string_list[self.state], self.state_string_list[self.next_state], token, self.command)
        if (0 < len(self.response_list)
        and token == self.response_list[0]
        and b'AT+CIPSEND' == self.command):
            # Sometimes, we get the mqtt packet after echo
            self.response_matches()
            self.response_list.insert(0, GPRS_RESPONSE_MQTT)
            return True
        self.response_mismatches(token)
        return False

    def method_match_pdp_deact(self, arg):
        '''
        Sometimes we get a spontaneous response of PDP: DEACT\r\n
        '''
        logging.info('Got PDP: DEACT %s %s', self.response_list, self.state_string_list[self.previous_state])
        if (1 == len(self.response_list)
        and GPRS_RESPONSE_OK == self.response_list[0]
        and self.state_string_to_int_dict['GPRS_STATE_CIICR'] == self.previous_state): # we have advanced to the next state already
            self.response_list = [GPRS_RESPONSE_SPONTANEOUS, GPRS_RESPONSE_ERROR]
        else:
            self.response_list = [GPRS_RESPONSE_SPONTANEOUS]
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
        self.response_matches()
        return True

    def method_match_cme_error(self, arg):
        '''
        CME ERROR
        '''
        logging.info('Got CME ERROR %s %s %s', arg, self.response_list, self.state_string_list[self.previous_state])
        # there may be an MQTT packet echoed from the radio here.  We need to flush that
        self.response_list = [GPRS_RESPONSE_SPONTANEOUS]
        self.next_state = self.state_string_to_int_dict['GPRS_STATE_FLUSH']
        self.response_matches()
        return True

    def method_match_goto_foo(self, token):
        '''
        handle jumping to the error state
        '''
        if (0 < len(self.response_list)
        and token == self.response_list[0]):
            self.response_matches()
            self.goto_foo()
            return True
        else:
            logging.error('method_match_goto_foo() called with non matching response token %d rather than the expected %d', token, self.response_list[0])
        self.response_mismatches(token)
        return False

    def method_match_open(self, arg):
        '''
        handle MQTT OPEN response
        '''
        if (0 == arg
        and 0 < len(self.response_list)
        and GPRS_RESPONSE_QMTOPEN == self.response_list[0]):
            self.connected = True
            self.response_matches()
            return True
        elif (2 == arg
        and 0 < len(self.response_list)
        and GPRS_RESPONSE_QMTOPEN == self.response_list[0]):
            # need to shut the connection (or just use it?)
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_MQTTSHUT']
            self.response_matches()
            logging.error('method_match_open() sees that the MQTT identifier is occupied')
            return True
        else:
            logging.error('method_match_open() called with non matching response token %d rather than the expected %d', GPRS_RESPONSE_QMTOPEN, self.response_list[0])
        return False

    def method_match_urc(self, arg):
        '''
        handle getting a spontaneous Unsolicited Result Code (URC)
        +QMTSTAT: 1,<arg>
        '''
        if 1 == arg: # Connection is closed or reset by peer
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_MQTTOPEN']
            self.response_list = [GPRS_RESPONSE_SPONTANEOUS]
            self.response_matches()
            return True


    def method_match_closed(self, arg):
        '''
        handle getting a spontaneous 'CLOSED\r\n'
        '''
        self.connected = False
        self.radio_busy = True # this is to get the code to go to the next_state
        self.output_timeout_start_time = time.time()
        self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
        self.response_list = [GPRS_RESPONSE_SPONTANEOUS]
        self.response_matches()
        return True

    def method_match_calr(self, arg):
        '''
        handle CALR parsing
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_CALR == self.response_list[0]):
            self.response_matches()
            self.call_ready = arg
            return True
        self.response_mismatches(GPRS_RESPONSE_CALR)
        return False

    def method_match_creg(self, arg):
        '''
        handle CREG parsing
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_REG == self.response_list[0]):
            self.response_matches()
            self.registered = arg
            return True
        self.response_mismatches(GPRS_RESPONSE_REG)
        return False

    def method_match_error(self, unused):
        '''
        handle ERROR parsing
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_ERROR == self.response_list[0]):
            self.next_state = self.state_string_to_int_dict['GPRS_STATE_IP_STATUS']
            self.response_matches()
            return True
        return self.method_match_goto_foo(GPRS_RESPONSE_ERROR)

    def method_match_sendfail(self, token):
        '''
        handle SEND FAIL parsing
        '''
        if (0 < len(self.response_list)
        and token == self.response_list[0]):
            self.successfully_published = False
            self.response_matches()
            return True
        self.response_mismatches(token)
        return False

    def method_match_connectfail(self, token):
        '''
        handle CONNECT FAIL parsing
        '''
        self.next_state = self.state_string_to_int_dict['GPRS_STATE_IPSHUT']
        self.response_matches() # flush the output and response list
        return True # we want to go to the next state

    def method_match_sendok(self, token):
        '''
        handle SEND OK parsing
        '''
        if (0 < len(self.response_list)
        and GPRS_RESPONSE_SENDOK == self.response_list[0]):
            # At this point, we have successfully published the message to the topic
            self.successfully_published = True
            self.response_matches()
            return True
        self.response_mismatches(GPRS_RESPONSE_SENDOK)
        return False

    def method_match_blank(self, token):
        # we just ignore blank lines in the output
        self.response_list.insert(0, token)
        self.response_matches()
        return True



    '''
    This is a dictionary of exact radio output lines and how to handle them
    '''
    METHODS = {
        b'\r\n': {'method': method_match_blank, 'arg': GPRS_RESPONSE_BLANK},
        b'OK\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_OK},
        b'SHUT OK\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_SHUTOK},
        b'SEND OK\r\n': {'method': method_match_sendok, 'arg': GPRS_RESPONSE_SENDOK},
        b'CONNECT OK\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_CONNECTOK},
        # there are echo responses
        b'AT\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIPSEND\r\n': {'method': method_premature_ipsend, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CGNSTST=0\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CMEE=1\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIPSPRT=0\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CCALR?\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CREG?\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CCLK?\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CSQ\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIPSHUT\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIPSTATUS\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CSTT="m2mglobal"\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIICR\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIFSR\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+CIPSTART="TCP","io.adafruit.com","1883"\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+QMTCLOSE=1\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+QMTOPEN=1,"io.adafruit.com",1883\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        b'AT+QMTCONN=1,"bg96","'+username.encode(encoding='UTF-8')+b'","'+password.encode(encoding='UTF-8')+b'"\r\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_ECHO},
        # these are IP STATUS responses
        b'STATE: IP INITIAL\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_CSTT'},
        b'STATE: IP START\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_CIICR'},
        b'STATE: IP GPRSACT\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_CIFSR'},
        b'STATE: IP STATUS\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_CIPSTART'},
        b'STATE: TCP CLOSED\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_IPSHUT'},
        b'STATE: PDP DEACT\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_IPSHUT'},
        b'STATE: CONNECT OK\r\n': {'method': method_match_ipstatus, 'arg': 'GPRS_STATE_IPSHUT'},
        # these are transient IP STATUS responses
        b'STATE: IP CONFIG\r\n': {'method': method_match_ipconfig, 'arg': 3},
        b'STATE: TCP CONNECTING\r\n': {'method': method_match_ipconfig, 'arg': 10},
        b'STATE: TCP CLOSING\r\n': {'method': method_match_ipconfig, 'arg': 3},
        # these are errors or unusual responses
        b'ERROR\r\n': {'method': method_match_error, 'arg': GPRS_RESPONSE_ERROR},
        b'SEND FAIL\r\n': {'method': method_match_sendfail, 'arg': GPRS_RESPONSE_SENDOK},
        b'CONNECT FAIL\r\n': {'method': method_match_connectfail, 'arg': GPRS_RESPONSE_CONNECTOK},
        b'CLOSED\r\n': {'method': method_match_closed, 'arg': 0},
        b'+PDP: DEACT\r\n': {'method': method_match_pdp_deact, 'arg': 0},
        b'AT+CIICR\r+PDP: DEACT\r\n': {'method': method_match_pdp_deact, 'arg': 0},
        #b'+CME ERROR: 3\r\n': {'method': method_match_cme_error, 'arg': 3},
        #b'+CME ERROR: 107\r\n': {'method': method_match_cme_error, 'arg': 107},
        # these could be done via regex
        b'+CCALR: 0\r\n': {'method': method_match_calr, 'arg': False},
        b'+CCALR: 1\r\n': {'method': method_match_calr, 'arg': True},
        b'+CREG: 0,0\r\n': {'method': method_match_creg, 'arg': False},
        b'+CREG: 0,1\r\n': {'method': method_match_creg, 'arg': True},
        b'+CREG: 0,2\r\n': {'method': method_match_creg, 'arg': False},
        b'+CREG: 0,5\r\n': {'method': method_match_creg, 'arg': True},
        b'+QMTCLOSE: 1,0\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_QMTCLOSE},
        b'+QMTOPEN: 1,0\r\n': {'method': method_match_open, 'arg': 0},
        b'+QMTOPEN: 1,2\r\n': {'method': method_match_open, 'arg': 2},
        b'+QMTCONN: 1,0,0\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_QMTCONN},
        b'+QMTPUB: 1,0,0\r\n': {'method': method_match_generic, 'arg': GPRS_RESPONSE_QMTPUB},
        b'+QMTSTAT: 1,1\r\n': {'method': method_match_urc, 'arg': 1}
    }

    def publish(self, topic, message):
        '''
        publish a message to an AdaFruit.IO topic by sending a packet out via the radio
        Note that this just starts the communication
        '''
        logging.debug('Bg96.publish() to %s', topic)
        if self.radio_busy:
            raise NotImplementedError
        if not self.connected:
            raise NotImplementedError
        packet = self.build_message_packet(topic, message)
        self.lasttopic = topic
        self.successfully_published = False
        self.send_command(b'AT+QMTPUB=1,0,0,0,"'
            +username.encode(encoding='UTF-8')
            +b'/feeds/'
            +topic.encode(encoding='UTF-8')
            +b'"', packet, [GPRS_RESPONSE_ECHO, GPRS_RESPONSE_PACKET, GPRS_RESPONSE_OK, GPRS_RESPONSE_QMTPUB],
             self.state_string_to_int_dict['GPRS_STATE_PUBLISH'])

