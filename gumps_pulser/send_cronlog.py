import os
import time

import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from requests.exceptions import HTTPError

from settings import *

with open('/home/dt/gumps_pulser/PulserName.txt', 'r') as pulsername_file:
    PULSER_NAME = pulsername_file.read()



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


def upload_pulser_stat_to_server(cronlog_file):
    token = login()
    urls = URL
    url = urls+'/api/PulserCronLog/'
    headers = {"Authorization": token}
    data = {'pulser': PULSER_NAME}
    files = {'cron_log': (os.path.basename(cronlog_file), open(
        cronlog_file, 'rb'))}
    try:
        resp = requests_retry_session().post(
            url, data=data, files=files, headers=headers)
    except requests.ConnectionError:
        print("Connection error")
    if resp.status_code == 201:
        print("Status File successfully sent to server")
    else:
        print("Unable to post status file to server")

def get_cronlog():
    upload_pulser_stat_to_server("/home/dt/logs/pulser.log")


if __name__ == '__main__':
    get_cronlog()
