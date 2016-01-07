#!/bin/bash

if [[ $(/usr/bin/id -u) -ne 0 ]] ; then
    echo "[e] Must be root to execute setup, exiting..."
    exit
fi

if [[ $(pwd | awk -F\/ '{ print $NF }') != "engine" ]] ; then
    echo "[e] Please execute setup.sh from the engine directory, exiting..."
    exit
fi

apt-get update
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to update package repository, exiting..."
    exit
fi

apt-get upgrade
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to update system, exiting..."
    exit
fi

apt-get install python-pip python-sqlite python-dev libbluetooth-dev libffi-dev libxml2-dev libxslt1-dev lib32z1-dev libssl-dev mongodb python-pymongo google-mock
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to install dependencies using apt-get, exiting..."
    exit
fi

pip install -r requirements.txt
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to install dependencies using pip, exiting..."
    exit
fi

