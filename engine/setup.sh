#!/bin/bash

DEFAULT_INSTALL_DIR="/opt/FuzzLabs/engine"
SELECTED_INSTALL_DIR=${DEFAULT_INSTALL_DIR}

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

if [[ $(pwd) != ${DEFAULT_INSTALL_DIR} ]] ; then
    echo -n "Install engine to ${DEFAULT_INSTALL_DIR}? [Y/n] "
    read CHOICE
    case ${CHOICE} in
        n|N)
            echo -n "Enter full path to install engine to: "
            read SELECTED_INSTALL_DIR
            ;;
    esac
    mkdir -p ${SELECTED_INSTALL_DIR}
    cp -R ./* ${SELECTED_INSTALL_DIR}
fi

cat "$(pwd)/etc/init.rc.sh" | sed "s@{{{ENGINE_HOME}}}@$SELECTED_INSTALL_DIR@" > /etc/init.d/engine
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi

chmod 700 /etc/init.d/engine
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi

ln -s /etc/init.d/engine /etc/rc2.d/S97engine.sh
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi

echo -n "Start engine now? [Y/n] "
read CHOICE
case ${CHOICE} in
    n|N)
        exit 0
        ;;
esac

echo "Starting engine..."
/etc/init.d/engine start
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to start engine, exiting..."
    exit 4
fi
echo "[e] Engine started successfully."
exit 0

