#!/usr/bin/env bash

ls src/pimpmyrice_server/*.py | entr -r pimp-server start
