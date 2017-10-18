# -*- coding: utf-8 -*-
import socket
from mpd import MPDClient
from .repeating_timer import RepeatingTimer

import logging
logger = logging.getLogger(__name__)

mpd_host = 'localhost'
mpd_port = 6600

def new_mpd_client():
        client = MPDClient()
        client.timeout = 20
        client.idletimeout = 20
        client.connect(mpd_host, mpd_port)
        return client
        

