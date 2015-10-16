#!/bin/bash

# Essentials
apt-get update
apt-get upgrade
apt-get install python-pip python-sqlite python-dev libbluetooth-dev libffi-dev libxml2-dev libxslt1-dev lib32z1-dev libssl-dev mongodb python-pymongo
pip install -r requirements.txt

