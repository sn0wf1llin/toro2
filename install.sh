#!/bin/bash

if [ `id -u` -ne 0 ]; then
  echo -e "\n[\e[91m!\e[0m] Root access Required."; exit 1
fi

PYTHON3_BIN=`which python3`

if [ -z $PYTHON3_BIN ]; then echo -e "[\e[91m!\e[0m] python3 required\n[\e[91m!\e[0m] Install python3 and restart the installation"; exit 1; fi
$PYTHON3_BIN toro2/toro2.py installnobackup
