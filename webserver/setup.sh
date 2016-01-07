#!/bin/bash

DEFAULT_INSTALL_DIR="/opt/FuzzLabs/webserver"
SELECTED_INSTALL_DIR=${DEFAULT_INSTALL_DIR}

if [[ $(/usr/bin/id -u) -ne 0 ]] ; then
    echo "[e] Must be root to execute setup, exiting..."
    exit
fi

if [[ $(pwd | awk -F\/ '{ print $NF }') != "webserver" ]] ; then
    echo "[e] Please execute setup.sh from the webserver directory, exiting..."
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

apt-get install python-pip python-sqlite python-dev libffi-dev libxml2-dev libxslt1-dev lib32z1-dev libssl-dev curl
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to install dependencies using apt-get, exiting..."
    exit
fi

pip install -r requirements.txt
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to install dependencies using pip, exiting..."
    exit
fi

# Not in use at the moment
#   curl --silent --location https://deb.nodesource.com/setup_4.x | sudo bash -
#   apt-get install --yes nodejs
#   npm install -g bower
#   bower install --allow-root

if [[ $(pwd) != ${DEFAULT_INSTALL_DIR} ]] ; then
    echo -n "Install web server to ${DEFAULT_INSTALL_DIR}? [Y/n] "
    read CHOICE
    case ${CHOICE} in
        n|N)
            echo -n "Enter full path to install web server to: "
            read SELECTED_INSTALL_DIR
            ;;
    esac
    mkdir -p ${SELECTED_INSTALL_DIR}
    cp -R ./* ${SELECTED_INSTALL_DIR}
fi

mkdir ${SELECTED_INSTALL_DIR}/etc/ssl
openssl genrsa -des3 -passout pass:x -out ${SELECTED_INSTALL_DIR}/etc/ssl/server.pass.key 2048
openssl rsa -passin pass:x -in ${SELECTED_INSTALL_DIR}/etc/ssl/server.pass.key -out ${SELECTED_INSTALL_DIR}/etc/ssl/server.key
rm ${SELECTED_INSTALL_DIR}/etc/ssl/server.pass.key
openssl req -new -key ${SELECTED_INSTALL_DIR}/etc/ssl/server.key -out ${SELECTED_INSTALL_DIR}/etc/ssl/server.csr
openssl x509 -req -days 365 -in ${SELECTED_INSTALL_DIR}/etc/ssl/server.csr -signkey ${SELECTED_INSTALL_DIR}/etc/ssl/server.key -out ${SELECTED_INSTALL_DIR}/etc/ssl/server.crt

cat "$(pwd)/etc/init.rc.collector.sh" | sed "s@{{{ENGINE_HOME}}}@$SELECTED_INSTALL_DIR@" > /etc/init.d/collector
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script for collector, exiting..."
    exit
fi
cat "$(pwd)/etc/init.rc.webserver.sh" | sed "s@{{{ENGINE_HOME}}}@$SELECTED_INSTALL_DIR@" > /etc/init.d/webserver
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script for web server, exiting..."
    exit
fi

chmod 700 /etc/init.d/collector
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi

chmod 700 /etc/init.d/webserver
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi 

ln -s /etc/init.d/collector /etc/rc2.d/S98collector.sh
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi

ln -s /etc/init.d/webserver /etc/rc2.d/S99webserver.sh
if [[ $? -ne 0 ]] ; then
    echo "[e] Failed to setup init script, exiting..."
    exit
fi  

echo -n "Start web server now? [Y/n] "
read CHOICE
case ${CHOICE} in
    n|N)
        exit 0
        ;;
esac

echo "Starting web server..."
/etc/init.d/collector start
sleep 1
/etc/init.d/webserver start
echo "[e] Web server started successfully."
exit 0

