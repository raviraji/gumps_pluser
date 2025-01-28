import gpio as GPIO
import serial
import time
from ip_func import *
import os
from subprocess import call
import datetime
import json
import sys
import glob
from datetime import datetime
from config_parser import *
from my_logger import get_logger
# --------Pulser code-------------

my_logger = get_logger(__name__)


class cont_pulse():
    def __init__(self):
        '''Server URLs to be set only once on init'''
        self.serv = ServerCommunications()  # Server communication related class
        self.pulser_name = self.serv.pulser_name_1
        self.wait_delay = 60
        self.Thr = 0
        self.TminFail = 1

        self.network_status = 1

        self.run_continuosly()

    def run_continuosly(self):
        while(1):
            try:  # (TEMPORARY): generic try and except - to log stack trace of unknown exceptions to log file
                try:
                    self.serv.get_date_time()
                except Exception as e:
                    my_logger.error("Unable to get date time", exc_info=True)
                try:
                    self.serv.get_config_file(self.pulser_name)
                except Exception as e:
                    my_logger.error(
                        "Unable to get config file from server", exc_info=True)
                # Pulser Config File related classes
                self.config_reader = Configuration()
                self.sig = SignalData()

                self.network_status = 0

                self.start_time = time.time()

                self.Tmin = self.config_reader.get_acq_rate()

                # reset microcontroller pins each time
                resetDelfino()
                time.sleep(10)

                self.configure_microcontroller()
                time.sleep(1)
                my_logger.info("\nStart:" + str(datetime.datetime.now()))

                # Get the list of pipes
                pipeList = self.config_reader.get_pipe_list()
                for pipe in pipeList:
                    # Get list of sensor combinations for particular pipe
                    sensor_combo_list = self.get_sensor_combo_list(pipe)

                    uploadDataFlag = True

                    for sensor_combo in sensor_combo_list:
                        my_logger.info(sensor_combo)

                        tx_port, rx_port = self.get_ports_for_one_sensor_combination(
                            sensor_combo)

                        if len(sys.argv) == 2:  # If switcher included, perform switching operation
                            my_logger.info("switcher included")
                            # Switching Tx/Rx
                            self.switch_pins_tx_rx(tx_port, rx_port)

                        else:
                            my_logger.info("no switcher")

                        serStatus, acqData = self.acquire_data()

                        uploadDataFlag &= serStatus

                        # Update data dictionary on valid pulser data
                        if(serStatus == 1 and len(acqData) > 0):
                            sensor_combo.update(
                                self.sig.save_data(acqData))

                    # Write to file and upload to server
                    if(uploadDataFlag):
                        self.uploadDataForPipe(sensor_combo_list)

                    if(self.network_status == 1):
                        self.upload_on_network_reconnection()

                my_logger.info(" End:" + str(datetime.datetime.now()))
                time_taken = (time.time()-self.start_time)/60
                my_logger.info("Total Time Taken- {}".format(time_taken))

                self.wait_delay = self.Thr*60+self.Tmin*60
                if(serStatus == 0):
                    my_logger.info("wrong path")
                    self.wait_delay = self.TminFail*60
                    my_logger.warn("Serial port failure!")
                my_logger.info(
                    "waiting after acq... acq-rate -> {}".format(self.wait_delay))
                time.sleep(self.wait_delay)

            except Exception as e:
                my_logger.critical(
                    "UNKNOWN ERROR - STACK TRACE ATTACHED", exc_info=True)

    def uploadDataForPipe(self, sensor_combo_list):
        self.clear_previous_acquisition()
        raw_data_json = {}
        raw_data_json['freq'] = self.config_reader.get_frequency()
        raw_data_json['sampling_freq'] = self.config_reader.get_sampling_freq(
        )
        raw_data_json['lower_cutoff_freq'] = self.config_reader.get_lower_cutoff_freq(
        )
        raw_data_json['upper_cutoff_freq'] = self.config_reader.get_upper_cutoff_freq(
        )
        raw_data_json['filter_order'] = self.config_reader.get_filter_order(
        )
        raw_data_json['buff_size'] = self.config_reader.get_buffers(
        )
        raw_data_json['sensor_combo'] = sensor_combo_list
        try:
            self.sig.upload_data(raw_data_json)
            self.network_status = 1
        except Exception as e:
            my_logger.error("Error in uploading data", exc_info=True)
            self.network_status = 0
            self.backup_unsaved_data(raw_data_json)

    def backup_unsaved_data(self, raw_data_json):
        my_logger.error("Backing up data locally")  # Saving data locally
        backupfolder = "/home/dt/gumps_pulser/UploadQ/"
        original_path = "/home/dt/gumps_pulser/"
        os.chdir(backupfolder)
        save_data_json(raw_data_json)
        self.network_status = 0
        os.chdir(original_path)

    def acquire_data(self):
        # Send Pulse to microcontroller
        serStatus, acqData = send_pulse_to_microcontroller()
        my_logger.info(serStatus)
        return serStatus, acqData

    def switch_pins_tx_rx(self, tx_port, rx_port):
        self.sig.sensor_data(tx_port, rx_port)

    def get_sensor_combo_list(self, pipe):
        return self.sig.get_tx_rx_combinations_for_pipe(pipe)

    def get_ports_for_one_sensor_combination(self, sensor_combo):
        try:
            tx = sensor_combo['transmitter']
            rx = sensor_combo['receiver']
        except KeyError:
            my_logger.error(
                "dictionary key 'txport'/'rxport' from json file failed.")
        if tx != rx:
            # getting switcher port
            tx_port = self.sig.get_port_for_sensor(tx)
            rx_port = self.sig.get_port_for_sensor(rx)
        else:
            my_logger.critical(
                "TX and RX should not be the same!")

        return tx_port, rx_port

    def clear_previous_acquisition(self):
        if(os.path.isfile("result.json.gz")):
            os.remove("result.json.gz")
        my_logger.info("Last acquisition cleared")

    def upload_on_network_reconnection(self):
        backupfolder = "/home/dt/gumps_pulser/UploadQ/"
        original_path = "/home/dt/gumps_pulser/"
        my_logger.info("Uploading Backup data")
        try:
            os.chdir(backupfolder)
            for backupfile in glob.glob("*.json"):
                with open(backupfile, "r") as file:
                    backupdata = file.read()
                    backupdata = json.loads(backupdata)
                self.sig.upload_data(backupdata)
                os.remove(os.path.join(backupfolder, backupfile))
                my_logger.info("BackUpData upload successful")
        except Exception as e:
            my_logger.error("Unable to upload backup data", exc_info=True)
            self.network_status = 0
        os.chdir(original_path)

    def configure_microcontroller(self):

        ser = serial.Serial()

        # serial setup
        ser.baudrate = 1000000
        ser.bytesize = serial.EIGHTBITS
        ser.parity = serial.PARITY_NONE
        ser.stopbits = serial.STOPBITS_ONE
        ser.timeout = 1

        # connect
        try:
            try:
                ser.port = '/dev/ttymxc5'
                ser.open()
            except:
                ser.port = '/dev/ttyUSB1'
                ser.open()

        except:
            my_logger.info("cannot open serial port")

        # set configuration
        my_logger.info("setting configuration")

        ##############################################################
        # perform a set config here for the new set of parameters
        ##############################################################

        freq = self.config_reader.set_frequency()
        my_logger.info(freq)

        while(not ser.write(str.encode('f'))):
            pass
        time.sleep(0.01)
        while(not ser.write(str.encode(freq))):
            pass
        time.sleep(2)

        flush(ser)
        ser.read(ser.inWaiting())

        ########set buffer size in hex########
        buf_set = self.config_reader.set_buffers()
        my_logger.info("read buffer")
        my_logger.info(buf_set)

        #######number of window/avgs########
        now_set = self.config_reader.set_window()
        my_logger.info("read now")
        my_logger.info(now_set)

        set_confg(ser, buf_set, now_set)
        time.sleep(2)
        my_logger.info("CONFIGURATION SETUP DONE")
        flush(ser)
        ser.close()


def send_pulse_to_microcontroller():
    ser = serial.Serial()

    # serial setup
    ser.baudrate = 1000000
    ser.bytesize = serial.EIGHTBITS
    ser.parity = serial.PARITY_NONE
    ser.stopbits = serial.STOPBITS_ONE
    ser.timeout = 1

    # connect
    try:
        try:
            ser.port = '/dev/ttymxc5'
            ser.open()
        except:
            ser.port = '/dev/ttyUSB1'
            ser.open()
    except:
        my_logger.info("cannot open serial port")
    # default values
    buf = 10000  # number of samples in one window
    now = 2048  # number of windows sampled
    err_flag = 0
    data = ''
    if ser.isOpen():
        my_logger.info("connection Established")
        try:
            ser.flushInput()
            ser.flushOutput()
            setup_delay(ser)
            my_logger.info(ser.read(ser.inWaiting()))
            [buf, now] = get_confg(ser)
        except Exception as e:
            my_logger.error("error in getting config")
            ser.close()
            return 0, data

        my_logger.info("****************************************")
        if(err_flag):
            time.sleep(2)
            my_logger.info(ser.read(50))
        else:
            time.sleep(2)
            flush(ser)
            n = ser.inWaiting()
            ser.read(n)
        my_logger.info("****************************************")

        # ip = raw_input("Type your action (h for help)  ")
        ip = 'c'
        time.sleep(10)
        if(ser.inWaiting()):
            my_logger.info("random data might be present")
            setup_delay(ser)
        elif(ip == 'c'):
            # Pulsar and Receiver Operates Simultaneously
            my_logger.info("Starting Acquisition")
            my_logger.info("Pulsing and Receiving Simultaneously")
            my_logger.info("windows # = {}".format(now))
            my_logger.info("buffer # = {}".format(buf))
            my_logger.info("please Wait")
            del data
        data = ''
        try:
            #######Acquire signals#######
            data = pulsar_receiver(ser, buf, now)
        except Exception as e:
            my_logger.error(e)
            my_logger.error("error in receiving data")
            ser.close()
            return 0, data
        ser.close()
        return 1, data
    else:
        return 0, data


def resetDelfino():
    '''Resetting Delfino'''
    # --------Reset code--------------
    # set up the GPIO channels - one input and one output
    GPIO.setup(33, GPIO.OUT)
    GPIO.output(33, GPIO.LOW)
    time.sleep(1)
    GPIO.output(33, GPIO.HIGH)
    time.sleep(1)
    my_logger.info("Reset Done")


if __name__ == '__main__':
    cont_pulse()
