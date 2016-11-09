# dexcom-tools
Tools for accessing from DEXCOM share and making it available in various ways.

Currently, the software will take the latest readings from dexcom share every 2.5 minutes.
For each reading, it will tell you the latest bg reading, the trend, and how old the reading is
So that we don't report duplicate values, readings are only sent to datadog if the timestamp has advanced.

# Datadog
I chose datadog because it has a great stat visualizing interface, can do alerting, and is free. 
Set up an account, an api and app key, put the values into the ini file, and datadog will graph things for you

# Installation

clone the repo
$ cd dexcom-tools

$ pip install --user -r requirements.txt

$ cp dexcom-tools.ini.example dexcom-tools.ini

# Edit dexcom-tools.ini
Put in your dexcom share (and any other ) credentials
change stat_name to something sensical, ie: jeremy.bg

# Usage

$ python dexcom-tools.py

# TODO

Portable desktop alerts
