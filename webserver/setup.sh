#!/bin/bash

# Essentials
apt-get update
apt-get upgrade
apt-get install python-pip python-sqlite python-dev libffi-dev libxml2-dev libxslt1-dev lib32z1-dev libssl-dev
pip install -r requirements.txt

mkdir ./etc/ssl
openssl genrsa -des3 -passout pass:x -out ./etc/ssl/server.pass.key 2048
openssl rsa -passin pass:x -in ./etc/ssl/server.pass.key -out ./etc/ssl/server.key
rm ./etc/ssl/server.pass.key
openssl req -new -key ./etc/ssl/server.key -out ./etc/ssl/server.csr
openssl x509 -req -days 365 -in ./etc/ssl/server.csr -signkey ./etc/ssl/server.key -out ./etc/ssl/server.crt

