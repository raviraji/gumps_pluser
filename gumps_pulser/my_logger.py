# -*- coding: utf-8 -*-

import logging
import sys
import os
import datetime
import requests
from logging.handlers import TimedRotatingFileHandler
from os.path import dirname, basename, exists, join, splitext
import shutil
from os import listdir, remove
import gzip
from zipfile import ZipFile

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


"""
Based on best practices from https://www.toptal.com/python/in-depth-python-logging
"""

FORMATTER = logging.Formatter(
    u"%(asctime)s — %(name)s — %(levelname)s — %(message)s")
LOG_FILE = "pulser_cont_pulse"


def get_console_handler():
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(FORMATTER)
    return console_handler


def get_file_handler():
    LOG_FOLDER_NAME = "logs"
    if not os.path.exists(LOG_FOLDER_NAME):
        os.mkdir(LOG_FOLDER_NAME)

    file_handler = CustomTimedRotatingFileHandler(
        # interval=2,
        filename=os.path.join(LOG_FOLDER_NAME, LOG_FILE), when='midnight',
        backupCount=2)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(FORMATTER)
    return file_handler


# def get_email_handler():
#     email_hadler = logging.handlers.SMTPHandler(fromaddr)

class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    # def __init__(self, filename="pulser_logs", when="midnight", interval=1,
    #              backup_count=2):
    #     super(CustomTimedRotatingFileHandler, self).__init__(
    #         filename=filename,
    #         when=when,
    #         interval=int(interval),
    #         backupCount=int(backup_count)
    #     )

    def doRollover(self):
        super(CustomTimedRotatingFileHandler, self).doRollover()
        log_dir = dirname(self.baseFilename)
        # to_compress = [
        #     join(log_dir, f) for f in listdir(log_dir) if f.startswith(
        #         basename(splitext(self.baseFilename)[0])
        #     ) and not f.endswith((".gz", ".log"))
        # ]
        to_compress = [
            join(log_dir, f) for f in listdir(log_dir) if '.' in f and not f.endswith((".gz", ".zip"))
        ]
        zip_filename = "pulser_log" + str(datetime.datetime.now())+".zip"
        curr_dir = os.getcwd()
        if basename(curr_dir) != "logs":
            os.chdir(join(curr_dir, "logs"))
        for file_path in to_compress:
            if exists(file_path):
             # with open(f, "r") as _old,
                with ZipFile(zip_filename, "w") as _new:
                    # shutil.copyfileobj(_old, _new)
                    _new.write(basename(file_path))
                remove(file_path)
        upload_log_to_server(join(os.getcwd(), zip_filename))
        remove(join(curr_dir, zip_filename))


def login():
    login_url = LOGIN_URL
    request_body = LOGIN_REQ_BODY
    resp = requests_retry_session().post(login_url, data=request_body)
    try:
        token_key = resp.json()['data']['token']
        #token_key = resp.json()['key']
    except KeyError:
        print("error invalid key")
    return "Token " + token_key


def upload_log_to_server(zip_file):
    token = login()
    urls = URL
    url = urls+'/api/PulserLog/'
    headers = {"Authorization": token}
    #with open('/home/dt/gumps_pulser/PulserName.txt', 'r') as pulsername_file:
    #        pulser_name = pulsername_file.read()
    pulser_name = PULSER_NAME
    data = {'pulser': pulser_name}
    files = {'pulser_log': (basename(zip_file), open(
        zip_file, 'rb'))}
    try:
        resp = requests_retry_session().post(
            url, data=data, files=files, headers=headers)
    except requests.ConnectionError:
        print("Connection error")
    if resp.status_code == 201:
        print("Log successfully sent to server")
    else:
        print("Unable to post log to server")
    os.remove(zip_file)


def get_logger(logger_name):
    logger = logging.getLogger(logger_name)
    if not len(logger.handlers):
        # better to have more logging details
        logger.setLevel(logging.DEBUG)
        logger.addHandler(get_console_handler())
        logger.addHandler(get_file_handler())
        # with this pattern, it's rarely necessary to propagate the error up to parent
        logger.propagate = False
    return logger

if __name__ == '__main__':
    global URL, LOGIN_URL, FERNET_PRIVATE_KEY, LOGIN_REQ_BODY, PULSER_NAME
    config = configparser.ConfigParser() 
    config.read('/home/dt/gumps_pulser/config.ini')
    URL = config.get('Server Settings', 'URL')
    LOGIN_URL = config.get('Server Settings', 'LOGIN_URL')
    FERNET_PRIVATE_KEY = config.get('Server Settings', 'FERNET_PRIVATE_KEY').encode()
    LOGIN_REQ_BODY = {"username": config.get('Server Settings', 'USERNAME'), "password": config.get('Server Settings', 'PASSWORD')}
    PULSER_NAME = config.get('Server Settings', 'PULSER_NAME')