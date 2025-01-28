import json
import datetime
import time
import requests
import subprocess
import gzip
import shutil
import gpio as GPIO
import logging
import base64
import configparser

from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import HTTPError
from cryptography.fernet import Fernet

from my_logger import get_logger


def requests_retry_session(retries=3,
                           backoff_factor=1,
                           status_forcelist=(500, 502, 504),
                           session=None):

    session = session or requests.Session()
    Retry.BACKOFF_MAX = 4*60
    retry = Retry(
        total=retries,
        read=0,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session


class FileHandler(object):
    def __init__(self, filename=""):
        self.filename = filename or "/home/dt/gumps_pulser/Pulser_Config.json"
        self.read_file()
        self.my_logger = get_logger(__name__)

    def read_file(self):
        try:
            with open(self.filename, "r") as f:
                self.file_data = json.load(f)
        except OSError as e:
            print(e)

    def read_signal_data(self):
        return self.file_data.get('sensor_combinations')

    def write_data(self, filename, data):
        with open(filename, "w") as f:
            f.write(data)

    def read_ports_data(self):
        return self.file_data.get('ports')

    def create_file_gzip(self, zip_file, json_file):
        try:
            with open(json_file,  'rb') as f_in:
                with gzip.open(zip_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
        except Exception as e:
            self.my_logger.error("Unable to gzip file")


class Configuration(object):
    def __init__(self, filename=""):
        self.file_reader = FileHandler(filename)
        self.load_config()
        self.freq_map_to_hex = {30000: '1', 35000: '2', 40000: '3', 45000: '4', 50000: '5', 55000: '6',
                                60000: '7', 65000: '8', 70000: '9', 75000: 'a', 80000: 'b', 85000: 'c', 90000: 'd', 95000: 'e'}
        self.buf_map_to_hex = {100: '1', 1000: '2', 10000: '3', 48000: '4', 15000: '5', 20000: '6'}
        self.window_map_to_hex = {16: '1', 64: '2', 128: '3', 256: '4', 512: '5', 1024: '6',
                                  2048: '7', 4096: '8'}

    def load_config(self):
        config_data = self.file_reader.file_data
        self._frequency = config_data.get('freq')
        self._buffers = config_data.get('buff_size')
        self._window = config_data.get('avgs')
        self._contact = config_data.get('cont_acq')
        self._acquisition_rate = config_data.get('acq_rate')
        # self._sensors = self.file_reader.read_signal_data()
        self._pulser = config_data.get('name')
        self._pipe_list = config_data.get('pipe')
        self._filter_order = config_data.get('filter_order')
        self._sampling_freq = config_data.get('sampling_freq')
        self._lower_cutoff_freq = config_data.get('lower_cutoff_freq')
        self._upper_cutoff_freq = config_data.get('upper_cutoff_freq')

    def get_frequency(self):
        return self._frequency

    def get_buffers(self):
        return self._buffers

    def get_window(self):
        return self._window

    def get_contact(self):
        return self._contact

    def get_acq_rate(self):
        return self._acquisition_rate

    def get_pulser_name(self):
        return self._pulser

    def get_filter_order(self):
        return self._filter_order

    def get_sampling_freq(self):
        return self._sampling_freq

    def get_lower_cutoff_freq(self):
        return self._lower_cutoff_freq

    def get_upper_cutoff_freq(self):
        return self._upper_cutoff_freq

    def set_frequency(self):
        '''Used for setting freq in microcontroller'''
        return self.freq_map_to_hex.get(self.get_frequency(), '1')

    def set_buffers(self):
        '''Used for setting buffer in microcontroller'''
        return self.buf_map_to_hex.get(self.get_buffers(), '3')

    def set_window(self):
        '''Used for setting window in microcontroller'''
        return self.window_map_to_hex.get(self.get_window(), '4')

    # def get_sensor_combinations(self):
    #     return self._sensors

    def get_pulser_name(self):
        return self._pulser

    def get_pipe_list(self):
        return self._pipe_list


class SignalData(object):
    def __init__(self, filename=""):
        self.file_reader = FileHandler(filename)
        self.load_signal_data()         # has all possible sensor combinations for that pulser
        self.load_hardware_ports()
        self.gpio_handler = GpioHandler()
        self.config = Configuration()
        self.my_logger = get_logger(__name__)

    def load_signal_data(self):
        self.signal_data = self.file_reader.read_signal_data()

    def get_tx_rx_combinations_for_pipe(self, pipe):
        return self.signal_data[pipe]

    def load_hardware_ports(self):
        self.hardware_ports = self.file_reader.read_ports_data()

    def get_port_for_sensor(self, sensor):
        return self.hardware_ports[sensor]

    def _get_pulser_configuration(self):
        """ Loads config for respective pulser to obtain data from pulser """
        config = Configuration()
        freq = config.get_frequency()
        buf = config.get_buffers()
        window = config.get_window()
        return freq, buf, window

    def map_sensornames_to_bits(self, sensor):
        sensor_name_to_bits = {"S1": '101', "S2": '001', "S3": '001',
                               "S4": '010', "S5": '011', "S6": '100', "S7": '000', "S8": '111'}
        return sensor_name_to_bits.get(sensor)

    def send_signal_data(self, current_signal_data):
        signal_string_data = ", ".join(str(z) for z in current_signal_data)
        date = datetime.datetime.now().strftime(
            "%Y-%m-%d")
        times = datetime.datetime.now().strftime(
            "%H:%M:%S")
        acquisition_data = {"date_info": date,
                            "time_info": times, "data": signal_string_data, "pipe": self.config.get_pipe_name(), "pulser": self.config.get_pulser_name()}
        for sensor in self.signal_data:
            tx_port = sensor.get('txport')
            rx_port = sensor.get('rxport')
            if tx_port != rx_port:
                self.sensor_data(tx_port, rx_port)
                sensor.update(acquisition_data)
            else:
                print("The same sensor can't act as transmitter and receiver")
        # self.deserialize_data(sensor_data)
        with open("Data.json", "w") as outfile:
            json.dump(self.signal_data, outfile)
        self.file_reader.create_file_gzip("result.json.gz", "Data.json")
        server_comm = ServerCommunications()
        server_comm.upload_data_to_server('result.json.gz')

    def deserialize_data(self, data):
        self.file_reader.write_data("Data.json", json.dump(data))

    def sensor_data(self, tx, rx):
        tx_bits = self.map_sensornames_to_bits(tx)
        rx_bits = self.map_sensornames_to_bits(rx)
        tx_gpio_pins = [tx_bits[i] for i in range(len(tx_bits))]
        rx_gpio_pins = [rx_bits[i] for i in range(len(rx_bits))]
        print(tx, tx_gpio_pins)
        print(rx, rx_gpio_pins)
        self.gpio_handler.tx_gpio(tx_gpio_pins)
        self.gpio_handler.rx_gpio(rx_gpio_pins)
        time.sleep(1)

    def save_data(self, acqData):
        signal_string_data = ", ".join(str(z) for z in acqData)
        date = datetime.datetime.now().strftime("%Y-%m-%d")
        times = datetime.datetime.now().strftime("%H:%M:%S")
        return {"date_info": date,
                            "time_info": times, "data": signal_string_data}

    def upload_data(self, signal_data):
        # convert data from dict to string
        signal_data = json.dumps(signal_data)
        # encrypt the data
        encrypted_signal_data = self.encrypt(signal_data)
        print("encrypted data")
        with open("EncryptedData.txt", "w") as outfile:
            outfile.write(encrypted_signal_data)
        self.file_reader.create_file_gzip(
            "result.json.gz", "EncryptedData.txt")
        server_comm = ServerCommunications()
        server_comm.upload_data_to_server('result.json.gz')

    def encrypt(self, data):
        try:
            # convert data to sring
            data = str(data)
            # get the key from settings, key should be byte
            cipher_suite = Fernet(FERNET_PRIVATE_KEY)
            # input should be byte, so convert the text to byte
            encrypted_text = cipher_suite.encrypt(data.encode('ascii'))
            # encode to urlsafe base64 format
            encrypted_text = base64.urlsafe_b64encode(
                encrypted_text).decode("ascii")
            return encrypted_text
        except TypeError:
            self.my_logger.error(
                "TYpe error - Data to be encrypted is not in bytes")
            self.my_logger.error(traceback.format_exc())


class GpioHandler(object):
    def __init__(self):
        #GPIO.setmode(GPIO.BOARD)
        #self.gpio_pins = [45, 44, 37, 36, 35, 34] old pulser config
        self.gpio_pins = [34, 35, 36, 37, 44, 45]
        for pin in self.gpio_pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        self.gpio_sig_out = {'1': GPIO.HIGH, '0': GPIO.LOW}

    def tx_gpio(self, tx_gpio_pins):
        for (pin, tx_pin) in zip(self.gpio_pins[:3], tx_gpio_pins):
            GPIO.output(pin, self.gpio_sig_out.get(tx_pin))

    def rx_gpio(self, rx_gpio_pins):
        for (pin, rx_pin) in zip(self.gpio_pins[3:6], rx_gpio_pins):
            GPIO.output(pin, self.gpio_sig_out.get(rx_pin))

    def reset_pins_to_low(self):
        for pin in self.gpio_pins[:3]:
            GPIO.output(pin, GPIO.LOW)
        for pin in self.gpio_pins[3:6]:
            GPIO.output(pin, GPIO.HIGH)

    def __del__(self):
        for pin in self.gpio_pins:
            GPIO.output(pin, self.gpio_sig_out.get('0'))


class ServerCommunications(object):
    def __init__(self):
        self.read_config_file()
        self.urls = URL
        self.login_url = LOGIN_URL
        self.pulser_name_1 = PULSER_NAME
        self.my_logger = get_logger(__name__)

    def read_config_file(self):
        global URL, LOGIN_URL, FERNET_PRIVATE_KEY, LOGIN_REQ_BODY, PULSER_NAME
        config = configparser.ConfigParser() 
        config.read('/home/dt/gumps_pulser/config.ini')
        URL = config.get('Server Settings', 'URL')
        LOGIN_URL = config.get('Server Settings', 'LOGIN_URL')
        FERNET_PRIVATE_KEY = config.get('Server Settings', 'FERNET_PRIVATE_KEY').encode()
        LOGIN_REQ_BODY = {"username": config.get('Server Settings', 'USERNAME'), "password": config.get('Server Settings', 'PASSWORD')}
        PULSER_NAME = config.get('Server Settings', 'PULSER_NAME')

    def login(self):
        request_body = LOGIN_REQ_BODY
        resp = requests_retry_session().post(self.login_url, data=request_body)
        if resp.status_code != 200:
            self.my_logger.critical("Unable to login to server. Response status is {} with the error {}".format(
                resp.status_code, resp.json()))
        try:
            token_key = resp.json()['data']['token']
            #token_key = resp.json()['key']
        except KeyError:
            self.my_logger.critical("Invalid key while requesting token!")
        self.token = "Token " + token_key

    def upload_data_to_server(self, jsonfilename):
        if not hasattr(self, 'token'):
            self.login()
        url = self.urls+'/api/RawDataFile/'
        headers = {'Content-Encoding': 'gzip',
                   "Authorization": self.token, 'Accept-Encoding': 'gzip'}
        with open(jsonfilename, 'rb') as json_file_handler:
            files = {'file': (jsonfilename, json_file_handler,
                              'applications/gzip')}
            try:
                resp = requests_retry_session().post(url, files=files, headers=headers)
            except requests.ConnectionError:
                self.my_logger.error(
                    "Exception error- Unable to upload. Please check internet and re-upload")
                raise requests.ConnectionError
            if resp.status_code == 204:
                self.my_logger.info("Data successfully sent to server")
            else:
                self.my_logger.critical("Data not uploaded to server!")
                resp.raise_for_status()
                raise requests.ConnectionError
                

    def get_date_time(self):
        if not hasattr(self, 'token'):
            self.login()
        print("trying to get date time from server")
        url = self.urls+'/api/GetDateTime'
        headers = {
            "Authorization": self.token}
        try:
            s = requests.Session()
            s.headers.update(headers)
            response = requests_retry_session(session=s).get(url)
        except Exception as e:
            print("Unable to connect to server")
        if response.status_code == 200:
            subprocess.call(['sudo', 'date', '-s', response.text])
        else:
            self.my_logger.error(response.json())

    def get_config_file(self, pulser_name):
        if not hasattr(self, 'token'):
            self.login()
        try:
            self._extracted_from_get_config_file_5(pulser_name)
        except requests.ConnectionError:
            self.my_logger.error(
                "Connection Error when trying to get Config file from server")

    def _extracted_from_get_config_file_5(self, pulser_name):
        print("trying to get get config file from server")
        url = self.urls + \
            '/api/DownloadSensorCombinations/?name={}'.format(pulser_name)
        headers = {
            "Authorization": self.token}
        s = requests.Session()
        s.headers.update(headers)
        response = requests_retry_session(session=s).get(url)
        print(response.json())
        if response.status_code == 200:
            f = FileHandler()
            f.write_data("Pulser_Config.json", json.dumps(response.json()))
        else:
            self.my_logger.error(
                "Expected response status 200, but got {}. Error details - {}".format(response.status_code, response.json()))

    def upload_log_to_server(self, zip_file):
        if not hasattr(self, 'token'):
            self.login()
        url = self.urls+'/api/PulserLog/'
        headers = {"Authorization": self.token}
        with open(zip_file, 'rb') as zip_file_handler:
            data = {'pulser_log': (zip_file, zip_file_handler,
                                   'application/zip'), 'pulser': 'MRPL-Pulser1A'}
            try:
                resp = requests_retry_session().post(url, data, headers=headers)
            except requests.ConnectionError:
                self.my_logger.error(
                    "Exception error- Unable to upload. Please check internet and re-upload")
                raise requests.ConnectionError
            if resp.status_code == 201:
                self.my_logger.info("Log successfully sent to server")
            else:
                self.my_logger.critical("Unable to post log to server")
                raise requests.ConnectionError


if __name__ == '__main__':
    server_comm = ServerCommunications()
    server_comm.login()
    # server_comm.get_config_file(PULSER_NAME)
