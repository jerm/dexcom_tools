# Credit
This started as a python rewrite/rework of much of the DexcomShare portion of [share2nightscount](https://github.com/nightscout/share2nightscout-bridge), a dexcom reporting piece of the most excellent NightScout project. I've skipped all the NS integration as I'm not using NightScout, though it should be easy enough to reimplement, if you like. 

# Description
(Paraphrased and updated from the share2nightscout description)
The program logs in to Dexcom Share as the data publisher. It re-uses the token every 2.5 minutes to fetch the latest glucose record. This information is then sent to the terminal and DataDog, making the data available to whomever the owner chooses. It will continue to re-use the same sessionID until it expires, at which point it should attempt to log in again. If it can log in again, it will continue to re-use the new token to fetch data.

So that we don't report duplicate values, readings are only sent to datadog if the timestamp has advanced.

# Datadog
I chose datadog because it has a great stat visualizing interface, can do alerting, and is free. 
Set up an account, an api and app key, put the values into the ini file, and datadog will graph things for you

# Webapp
In order to make this easily query-able from... other things... I've added
webapp.py and webapp.ini.example to make the readings available via a
"serverless" web endpoint using flask and zappa.io. Follow steps on zappa.io
page to deploy.

Example:
![example datadog graph](https://d3vv6lp55qjaqc.cloudfront.net/items/071D2b3x1n3x1Z3n1V2J/datadog_example_graph.png)

# Installation

clone the repo

$ cd dexcom_tools

$ pip install --user -r requirements.txt

$ cp dexcom_tools.ini.example dexcom_tools.ini

# Edit dexcom_tools.ini
Put in your dexcom share (and any other ) credentials
change stat_name to something sensical, ie: jeremy.bg

# Usage

$ python dexcom_tools.py

# TODO
Better docs for webapp/lamba deploy

Portable desktop alerts

slack/sms/etc.. alerts
