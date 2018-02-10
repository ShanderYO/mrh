# -*- coding: utf-8 -*-
import socket
import os
from mpd import MPDClient
from .repeating_timer import RepeatingTimer
import time
import logging
mpd_host = '127.0.0.1'
mpd_port = 6600

logger = logging.getLogger(__name__)

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
            logger.warning(es)
            c += 1
            time.sleep(1)

        if c >= 5:
            break
    return client

def clear_playlist(client):
    '''
        Remove all track of current playlist expect current track
    '''
    while True:
        status = client.status()
        if status['playlistlength'] in ['0', '1']:
            break
        if hasattr(status, 'song') and status['song'] != '0':
            client.delete(0)
        else:
            client.delete(1)

def clear_not_exists(client):
    '''
        Remove track with no files
    '''
    tracks = client.playlistinfo()
    tracks.sort(key=lambda i:int(i['pos']), reverse=True)
    for track in tracks:
        if not os.path.exists(track['file']):
            client.delete(int(track['pos']))
            # logger.info('Track %s remove from playlist' % track['file'])

