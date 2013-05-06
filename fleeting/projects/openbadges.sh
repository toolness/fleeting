#! /bin/bash

# fleeting-meta:name          = Open Badges Backpack
# fleeting-meta:repo          = mozilla/openbadges
# fleeting-meta:image-id      = ami-2bb7d442
# fleeting-meta:instance-type = t1.micro
# fleeting-meta:ready-url     = http://localhost:8888/

export DEBIAN_FRONTEND=noninteractive
export PUBLIC_HOSTNAME=`ec2metadata --public-hostname`

# Needed by node-gyp. For more info, see:
# https://github.com/TooTallNate/node-gyp/issues/21#issuecomment-17494117
export HOME=/home/ubuntu

# Taken from:
# https://github.com/joyent/node/wiki/Installing-Node.js-via-package-manager

apt-get -q -y update
apt-get -q -y install python-software-properties python g++ make
add-apt-repository -y ppa:chris-lea/node.js
apt-get -q -y update
apt-get -q -y install nodejs git mysql-server

git clone --recursive -b {{GIT_BRANCH}} \
  git://github.com/{{GIT_USER}}/openbadges.git

if [ -a /home/ubuntu/node_modules ]
  then mv /home/ubuntu/node_modules openbadges/
fi

cd openbadges

cat lib/environments/local-dist.js \
  | sed "s/hostname: 'localhost'/hostname: '${PUBLIC_HOSTNAME}'/" \
  > lib/environments/local.js

mysql -e 'create database if not exists openbadges;'
mysql -e 'create database if not exists test_openbadges;'
mysql -uroot -e "grant all on openbadges.* to 'badgemaker'@'localhost' \
  identified by 'secret'"
mysql -uroot -e "grant all on test_openbadges.* to 'badgemaker'@'localhost' \
  identified by 'secret'"

npm install --production
make start-issuer
npm start
