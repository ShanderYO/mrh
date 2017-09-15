# -*- coding: utf-8 -*-
import socket
from mpd import MPDClient
from .repeating_timer import RepeatingTimer

import logging
logger = logging.getLogger(__name__)

def new_mpd_client():
        client = MPDClient()
        client.timeout = 20
        client.idletimeout = 20
        client.connect("localhost", 6602)
        return client

class Client(object):

    def __init__(self):
        self.client = MPDClient()
        self.client.timeout = 20
        self.client.idletimeout = 20
        self._connect_timer = RepeatingTimer(self.connect, 3)
        self._connect_timer.start()
        
    def connect(self):
    	try:
            self.client.connect("localhost", 6602)
        except socket.error:
            logger.info('Connect error!')
        else:
            self._connect_timer.cancel()
            self.load_playlist('main')
            self.client.consume(1)
            # self.client.crossfade(1)
            # self.client.mixrampdb(-17)
            # self.client.mixrampdelay(2)

    def load_playlist(self, id):
        if not len(self.client.playlistinfo()):
    	   self.client.load(id)
        if self.client.status()['state'] != 'play':
    	   self.client.play()

    def get_status(self):
        try:
            logger.info(self.client.status())
        except:
            pass

MPD = Client()
        

