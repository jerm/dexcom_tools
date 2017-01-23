#!/usr/bin/env python
import ConfigParser
import dexcom_tools
import logging

from flask import Flask
app = Flask(__name__)
Config = ConfigParser.ConfigParser()
Config.read("webapp.ini")

keyed_url_route = "/dexcom/{}".format(Config.get("webapp","auth_key"))
@app.route('/')
def hello_world():
    return 'Hello, World!'

#@app.route('/dexcom/0938o4yi2hkerugshrgo9a38oyw4liteh')
@app.route(keyed_url_route)
def dexcom():
    reading = dexcom_tools.query_dexcom()
    if reading:
        if reading['reading_lag'] < 600:
            if reading['trend_english'] == 'nodir':
                trend = ""
            else:
                trend = "trending {}, ".format(reading['trend_english'])
            message = "Blood sugar {}, {}as of {:.1f} minutes ago".format(
                    reading['bg'],
                    trend,
                    reading['reading_lag']/60.0
                    )
        else:
            message = "No recent readings"
    else:
        message =  "I fear somethign terrible has happened"
    return message

if __name__ == '__main__':
    app.run()
