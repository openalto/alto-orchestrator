#!/usr/bin/env bash
#
#
# This script downloads and installs for debian:
#
# - fireqos
# - fdt
# - pyro4
# - fdtclient

mkdir fireqos
cd fireqos

yum install zlib-devel libuuid-devel libmnl-devel gcc make git autoconf autogen automake pkgconfig traceroute ipset curl nodejs zip unzip jq ulogd

wget https://raw.githubusercontent.com/firehol/netdata-demo-site/master/install-all-firehol.sh

chmod 777 install-all-firehol.sh

./install-all-firehol.sh

cd ..

mkdir alto-fdtclient

cd alto-fdtclient

wget http://monalisa.cern.ch/FDT/lib/fdt.jar
wget https://raw.githubusercontent.com/openalto/alto-orchestrator/master/miscellaneous/fdtclient/fdtclient_srl.py
wget https://raw.githubusercontent.com/openalto/alto-orchestrator/master/miscellaneous/fdtclient/ip2interface2rate

if command -v python3 &>/dev/null; then
    pip3 install Pyro4
else
    sudo yum install python34-setuptools
    sudo easy_install-3.4 pip
    pip3 install Pyro4
fi

mkdir fireqos-confs
