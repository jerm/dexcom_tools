#!/usr/bin/env python
import ConfigParser
import dexcom_tools

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
            message = "Blood sugar {}, trending {}, as of {:.1f} minutes ago".format(
                    reading['bg'],
                    reading['trend_english'],
                    reading['reading_lag']/60.0
                    )
        else:
            message = "No recent readings"
    else:
        message =  "I fear somethign terrible has happened"
    return message

if __name__ == '__main__':
    app.run()
