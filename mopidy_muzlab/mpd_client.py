# -*- coding: utf-8 -*-
import socket
from mpd import MPDClient
from .repeating_timer import RepeatingTimer
import time
import logging
mpd_host = '127.0.0.1'
mpd_port = 6600

def new_mpd_client():
    client = MPDClient()
    client.timeout = 60
    client.idletimeout = 120
    c = 0
    while True:
        try:
            client.connect(mpd_host, mpd_port)
            break
        except Exception as es:
            logging.warning(es)
            c += 1
            time.sleep(1)

        if c >= 5:
            break
    return client