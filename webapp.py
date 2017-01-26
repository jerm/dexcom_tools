#!/usr/bin/env python
import ConfigParser
import dexcom_tools
import logging

from flask import Flask
app = Flask(__name__)
Config = ConfigParser.ConfigParser()
Config.read("webapp.ini")
PERSON=Config.get("webapp","person")

keyed_url_route = "/dexcom/{}".format(Config.get("webapp","auth_key"))
@app.route('/')
def hello_world():
    return 'Hello, World!'
response = """{
  "version": "1.0",
  "response": {
    "outputSpeech": {
      "type": "PlainText",
      "text": "DEXCOMRESPONSE"
    },
    "card": {
      "type": "Simple",
      "title": "Dexcom",
      "content": "DEXCOMRESPONSE"
    },
    "reprompt": {
      "outputSpeech": {
 "type": "PlainText",
 "text": "DEXCOMRESPONSE"
      }
    },
    "shouldEndSession": true
  },
  "sessionAttributes": {}
}
"""
#@app.route('/dexcom/0938o4yi2hkerugshrgo9a38oyw4liteh')
@app.route(keyed_url_route, methods=['GET', 'POST'])
def dexcom():
    reading = dexcom_tools.query_dexcom()
    if reading:
        if reading['reading_lag'] < 600:
            if reading['trend_english'] == 'nodir':
                trend = ""
            else:
                trend = "trending {}, ".format(reading['trend_english'])
            message = "Well, {}'s Blood sugar is {}, {}as of {:.1f} minutes ago".format(
                    PERSON,
                    reading['bg'],
                    trend,
                    reading['reading_lag']/60.0
                    )
        else:
            message = "Oh, There are no recent readings"
    else:
        message =  "I fear somethign terrible has happened"
    return response.replace("DEXCOMRESPONSE",message)

def adhoc_monitor():
    dexcom_tools.adhoc_monitor()

if __name__ == '__main__':
    app.run()
