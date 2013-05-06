#! /bin/bash

# fleeting-meta:name          = Chicago Summer of Learning Site
# fleeting-meta:repo          = mozilla/CSOL-site
# fleeting-meta:image-id      = ami-2bb7d442
# fleeting-meta:instance-type = t1.micro
# fleeting-meta:ready-url     = http://localhost:3000/

export DEBIAN_FRONTEND=noninteractive
export COOKIE_SECRET="TESTING"

# Taken from:
# https://github.com/joyent/node/wiki/Installing-Node.js-via-package-manager

apt-get -q -y update
apt-get -q -y install python-software-properties python g++ make
add-apt-repository -y ppa:chris-lea/node.js
apt-get -q -y update
apt-get -q -y install nodejs git mysql-server

git clone --recursive -b {{GIT_BRANCH}} \
  git://github.com/{{GIT_USER}}/CSOL-site.git

cd CSOL-site

mysql -e 'create database if not exists csol;'

npm install --production
node app.js
