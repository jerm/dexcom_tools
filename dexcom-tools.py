#!/usr/bin/env python

import ConfigParser
import datetime
import json
import logging
import os
import re
import requests
import time
import urllib
#import notify

from datadog import api as dogapi
from datadog import initialize as doginitialize
from datadog import ThreadStats as dogThreadStats
from requests.exceptions import ConnectionError

Config = ConfigParser.ConfigParser()
Config.read("dexcom-tools.ini")

# create logger
log = logging.getLogger(__file__)
log.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
fh = logging.FileHandler('dexcom-tools.log')
fh.setLevel(logging.INFO)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)

# create formatter and add it to the handlers
formatter = logging.Formatter('{"timestamp": "%(asctime)s", "progname": "%(name)s", "loglevel": "%(levelname)s", "message":, "%(message)s"}')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
log.addHandler(fh)
log.addHandler(ch)

dd_options = {
    'api_key': Config.get("datadog","dd_api_key"),
    'app_key': Config.get("datadog","dd_api_key")
}

try:
    HEALTHCHECK_URL = Config.get("healthcheck","url")
except:
    HEALTHCHECK_UTL = None
datadog_stat_name = Config.get("datadog","stat_name")
DEXCOM_ACCOUNT_NAME = Config.get("dexcomshare","dexcom_share_login")
DEXCOM_PASSWORD = Config.get("dexcomshare","dexcom_share_password")
CHECK_INTERVAL = 60 * 2.5
AUTH_RETRY_DELAY_BASE = 2
FAIL_RETRY_DELAY_BASE = 2
MAX_AUTHFAILS = 10
MAX_FETCHFAILS = 10
LAST_READING_MAX_LAG = 60 * 15

last_date = 0;
notify_timeout = 5;
notify_bg_threshold = 170;
notify_rate_threshold = 10;
tempsilent = 0;

class Defaults:
    applicationId = "d89443d2-327c-4a6f-89e5-496bbb0317db"
    agent = "Dexcom Share/3.0.2.11 CFNetwork/711.2.23 Darwin/14.0.0"
    login_url = "https://share1.dexcom.com/ShareWebServices/Services/General/LoginPublisherAccountByName"
    accept = 'application/json'
    content_type = 'application/json'
    LatestGlucose_url = "https://share1.dexcom.com/ShareWebServices/Services/Publisher/ReadPublisherLatestGlucoseValues"
    sessionID = None
    nightscout_upload = '/api/v1/entries.json'
    nightscout_battery = '/api/v1/devicestatus.json'
    MIN_PASSPHRASE_LENGTH = 12
    last_seen = 0

# Mapping friendly names to trend IDs from dexcom
DIRECTIONS = {
    "nodir": 0,
    "DoubleUp": 1,
    "SingleUp": 2,
    "FortyFiveUp": 3,
    "Flat": 4,
    "FortyFiveDown": 5,
    "SingleDown": 6,
    "DoubleDown": 7,
    "NOT COMPUTABLE": 8,
    "RATE OUT OF RANGE": 9,
}
keys = DIRECTIONS.keys()

def login_payload(opts):
    """ Build payload for the auth api query """
    body = {
        "password": opts.password
        , "applicationId" : opts.applicationId
        , "accountName": opts.accountName
        }
    return body;

def authorize(opts):
    """ Login to dexcom share and get a session token """

    url = Defaults.login_url
    body = login_payload(opts)
    headers = { 'User-Agent': Defaults.agent
        , 'Content-Type': Defaults.content_type
        , 'Accept': Defaults.accept
    }

    return requests.post(url, json=body, headers=headers)


def fetch_query(opts):
    """ Build the api query for the data fetch
    """
    q = {
        "sessionID": opts.sessionID
        , "minutes":  1440
        , "maxCount": 1
    }
    url = Defaults.LatestGlucose_url + '?' + urllib.urlencode(q);
    return url;

def fetch(opts):
    """ Fetch latest reading from dexcom share
    """
    url = fetch_query(opts);
    body = {'accountName': opts.accountName,
         'applicationId': 'd89443d2-327c-4a6f-89e5-496bbb0317db',
          'password': opts.password}

    headers = { 'User-Agent': Defaults.agent
        , 'Content-Type': Defaults.content_type
        , 'Content-Length': "0"
        , 'Accept': Defaults.accept
        }

    return requests.post(url, json=body, headers=headers)


class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class AuthError(Error):
    """Exception raised for errors when trying to Auth to Dexcome share
    """

    def __init__(self, status_code, message):
        self.expression = status_code
        self.message = message
        log.error(message.__dict__)

class FetchError(Error):
    """Exception raised for errors in the date fetch.
    """

    def __init__(self, status_code, message):
        self.expression = status_code
        self.message = message
        log.error(message.__dict__)

def to_datadog(mgdl,reading_lag):
    """ Send latest reading to datadog. Maybe create events on some critera
    """
    stats = dogThreadStats()
    stats.start()
    stats.gauge(datadog_stat_name, mgdl)
    stats.gauge("jermops.goo", mgdl)
    log.info("Sent bg {} to Datadog".format(mgdl))

    #if reading_lag > LAST_READING_MAX_LAG:
        #title = "Something big happened!"
        #text = 'And let me tell you all about it here!'
        #tags = ['version:1', 'application:web']
        #dogapi.Event.create(title=title, text=text, tags=tags)


def report_glucose(opts, res):
    """ Basic output """
    epochtime =  int((datetime.datetime.utcnow() -
        datetime.datetime(1970,1,1)).total_seconds())
    try:
        last_reading_time = int(re.search('\d+', res.json()[0]['ST']).group())/1000
        reading_lag = epochtime - last_reading_time
        trend = res.json()[0]['Trend']
        mgdl = res.json()[0]['Value']
        trend_english = DIRECTIONS.keys()[DIRECTIONS.values().index(trend)]
        log.info("Last bg: {}  trending: {}  last reading at: {} seconds ago".format(mgdl,trend_english,reading_lag))
        if reading_lag > LAST_READING_MAX_LAG:
            log.warning("***WARN It has been {} minutes since DEXCOM got a new measurement".format(int(reading_lag/60)))

        if last_reading_time > opts.last_seen:
            to_datadog(mgdl, reading_lag)
            opts.last_seen = last_reading_time
    except IndexError:
        log.error("IndexError: return code:{} ... response output below".format(res.status_code))
        log.error(res)


def monitor_dexcom():
    """ Main loop """

    doginitialize(**dd_options)
    opts = Defaults
    opts.accountName = os.getenv("DEXCOM_ACCOUNT_NAME", DEXCOM_ACCOUNT_NAME)
    opts.password = os.getenv("DEXCOM_PASSWORD", DEXCOM_PASSWORD)
    opts.interval = os.getenv("CHECK_INTERVAL", CHECK_INTERVAL)

    runs = 0
    fetchfails = 0
    failures = 0
    while True:
        try:
            if HEALTHCHECK_URL:
                requests.get(HEALTHCHECK_URL)
        except ConnectionError as e:
            log.error("Error sending heartbeat: {}".format(e))

        log.info("RUNNING {}, failures: {}".format(runs, failures))
        runs += 1
        if not opts.sessionID:
            authfails = 0
            while not opts.sessionID:
                res = authorize(opts)
                if res.status_code == 200:
                    opts.sessionID = res.text.strip('"')
                    log.debug("Got auth token {}".format(opts.sessionID))
                else:
                    if authfails > MAX_AUTHFAILS:
                        raise AuthError(res.status_code, res)
                    else:
                        log.warning("Auth failed with thing {}".format(res.status_code))
                        time.sleep(AUTH_RETRY_DELAY_BASE**authfails)
                        authfails += 1
        if runs == 0:
            log.debug("First time, fetching")
        try:
            res = fetch(opts)
            if res and res.status_code < 400:
                fetchfails = 0
                #import ipdb; ipdb.set_trace()
                report_glucose(opts, res)
                #import ipdb; ipdb.set_trace()
                time.sleep(opts.interval)
            else:
                failures += 1
                if fetchfails > MAX_FETCHFAILS:
                    raise FetchError(res.status_code, res)
                else:
                    log.warning("Fetch failed with thing: {}".format(res.status_code))
                    if fetchfails > (MAX_FETCHFAILS/2):
                        log.warning("Trying to re-auth...")
                        opts.sessionID = None
                    else:
                        log.warning("Trying again...")
                    time.sleep(FAIL_RETRY_DELAY_BASE**authfails)
                    fetchfails += 1
        except ConnectionError:
            log.warning("Cnnection Error.. sleeping for 60 seconds and trying again")
            sleep(60)

if __name__ == '__main__':
    monitor_dexcom()


