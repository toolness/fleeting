#! /bin/bash

# fleeting-meta:name          = Popcorn Maker
# fleeting-meta:repo          = mozilla/butter
# fleeting-meta:image-id      = ami-2bb7d442
# fleeting-meta:instance-type = t1.micro
# fleeting-meta:ready-url     = http://localhost:8888/

export DEBIAN_FRONTEND=noninteractive
export hostname="http://`ec2metadata --public-hostname`:8888"

# Taken from:
# https://github.com/joyent/node/wiki/Installing-Node.js-via-package-manager

apt-get -q -y install python-software-properties python g++ make
add-apt-repository -y ppa:chris-lea/node.js
apt-get -q -y update
apt-get -q -y install nodejs git mysql-server

git clone --recursive -b {{GIT_BRANCH}} \
  git://github.com/{{GIT_USER}}/butter.git

cd butter

npm install --production
npm start
