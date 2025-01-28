import os
import time
from subprocess import *

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import HTTPError
import configparser


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


def measure_temp():
    flags = os.O_RDWR | os.O_CREAT
    mode = 0o666
    temp = open("/sys/class/thermal/thermal_zone0/temp", 'r').read()
    return (temp[:2])


def measure_wifi_strength():
    shell_cmd = 'iwconfig'  # {} | grep Link'.format('wlx503eaa4f0b2d')
    proc = Popen(shell_cmd, shell=True, stdout=PIPE, stderr=PIPE)
    output, err = proc.communicate()
    msg = output.decode('utf-8').strip()
    print(msg)
    return msg


def login():
    login_url = LOGIN_URL
    request_body = LOGIN_REQ_BODY
    resp = requests_retry_session().post(login_url, data=request_body)
    try:
        #token_key = resp.json()['key']
        token_key = resp.json()['data']['token']
    except KeyError:
        print("error invalid key")
    return "Token " + token_key


def upload_pulser_stat_to_server():
    token = login()
    urls = URL  # local
    url = urls+'/api/PulserStat/'
    headers = {"Authorization": token}
    data = {'pulser': PULSER_NAME}
    files = {'pulser_stat': ("pulser_stat_file.txt", open(
        "pulser_stat_file.txt", 'rb'))}
    try:
        resp = requests_retry_session().post(
            url, data=data, files=files, headers=headers)
    except requests.ConnectionError:
        print("Connection error")
    if resp.status_code == 201:
        print("Status File successfully sent to server")
    else:
        print("Unable to post status file to server")
        


if __name__ == '__main__':
    global URL, LOGIN_URL, LOGIN_REQ_BODY, PULSER_NAME
    config = configparser.ConfigParser() 
    config.read('/home/dt/gumps_pulser/config.ini')
    URL = config.get('Server Settings', 'URL')
    LOGIN_URL = config.get('Server Settings', 'LOGIN_URL')
    FERNET_PRIVATE_KEY = config.get('Server Settings', 'FERNET_PRIVATE_KEY').encode()
    LOGIN_REQ_BODY = {"username": config.get('Server Settings', 'USERNAME'), "password": config.get('Server Settings', 'PASSWORD')}
    PULSER_NAME = config.get('Server Settings', 'PULSER_NAME')
    temp = measure_temp()
    print(temp)
    time.sleep(1)
    wifi_msg = measure_wifi_strength()
    time.sleep(1)

    with open("pulser_stat_file.txt", "w") as pulser_stat_file:
        pulser_stat_file.write("Temp: {}".format(temp))
        pulser_stat_file.write("\nWifi details \n {}".format(wifi_msg))

    upload_pulser_stat_to_server()
