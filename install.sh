#!/bin/bash

# unzip toro2.zip
PYTHON3_BIN=`which python3`

if [ -z $PYTHON3_BIN ]; then echo -e "[\e[91m!\e[0m] python3 required\n[\e[91m!\e[0m] Install python3 and restart the installation"; exit 1; fi
$PYTHON3_BIN /opt/toro2/toro2/toro2.py installnobackup
