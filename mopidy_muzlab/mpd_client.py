# -*- coding: utf-8 -*-
import socket
from os.path import isfile
from mpd import MPDClient, CommandError, _NotConnected, ConnectionError
from .repeating_timer import RepeatingTimer
from .utils import get_rotation_id, get_played_rotation, get_next_load_tracks, get_last_start_id
import time
import logging
import warnings
from collections import deque
mpd_host = '127.0.0.1'
mpd_port = 6600

logger = logging.getLogger(__name__)


class NewMPDClient(MPDClient):

    def connect(self, host, port, timeout=None):
        logger.debug("Calling MPD connect(%r, %r, timeout=%r)", host,
                    port, timeout)
        if self._sock is not None:
            raise ConnectionError("Already connected")
        if timeout is not None:
            warnings.warn("The timeout parameter in connect() is deprecated! "
                          "Use MPDClient.timeout = yourtimeout instead.",
                          DeprecationWarning)
            self.timeout = timeout
        if host.startswith("/"):
            self._sock = self._connect_unix(host)
        else:
            self._sock = self._connect_tcp(host, port)

        self._rfile = self._sock.makefile("r")
        self._wfile = self._sock.makefile("w")

        try:
            self._hello()
        except:
            self.disconnect()
            raise

    def disconnect(self):
        logger.debug("Calling MPD disconnect()")
        if (self._rfile is not None
                and not isinstance(self._rfile, _NotConnected)):
            self._rfile.close()
        if (self._wfile is not None
                and not isinstance(self._wfile, _NotConnected)):
            self._wfile.close()
        if self._sock is not None:
            self._sock.close()
        self._reset()

def new_mpd_client():
    client = NewMPDClient()
    client.timeout = 120
    client.idletimeout = 180
    c = 0
    while True:
        try:
            client.connect(mpd_host, mpd_port, timeout=120)
            client.currentsong()
            break
        except Exception as es:
            logger.warning(es)
            c += 1
            time.sleep(1)

        if c >= 5:
            break
    return client

def mpd_connect(fn):
    def wrapped(*args, **kwargs):
        client = new_mpd_client()
        result = fn(client, *args, **kwargs)
        client.disconnect()
        return result
    return wrapped

@mpd_connect
def clear_playlist(client):
    '''
        Remove all track of current playlist expect current track
    '''
    while True:
        status = client.status()
        try:
            i = int(status['song']) + 2
        except KeyError:
            break
        try:
            client.delete(i)
        except ConnectionError:
            client = new_mpd_client()
            client.delete(i)
        except CommandError:
            pass
    logger.info('Playlist was cleared')

def load_playlist(playlist='main'):
    clear_playlist()
    client = new_mpd_client()
    client.load(playlist)
    clear_replays()

@mpd_connect
def clear_replays(client, clear_number=30):
    '''
        Remove repitead track from playlist
    '''

    logger.info('Start cleared replays')
    try:
        status = client.status()
        playlist = client.playlistinfo()
    except:
        return
    if not playlist:
        return
    try:
        pos = int(status['song'])
    except KeyError:
        pos = 0
    try:
        current_rotation = get_rotation_id(client.currentsong()['title'])
    except KeyError:
        current_rotation = None
    played = get_played_rotation()[-clear_number:]
    played.append(current_rotation)
    delete_ids = []
    for entry in playlist:
        if int(entry['pos']) <= pos:
            continue
        id_ = get_rotation_id(entry['title'])
        if id_ and id_ in played:
            delete_ids.append(int(entry['id']))
        else:
            played.append(id_)
    client = new_mpd_client()
    for i in delete_ids:
        try:
            client.deleteid(i)
        except ConnectionError:
            client = new_mpd_client()
            client.deleteid(i)
        except CommandError:
            pass
    logger.info('Playlist was checked on replays and cleared')

@mpd_connect
def clear_not_accepted(client):
    '''
        Remove track with no files
    '''
    tracks = client.playlistinfo()
    tracks.sort(key=lambda i:int(i['pos']), reverse=True)
    for track in tracks:
        if not isfile(track['file']):
            client.delete(int(track['pos']))
            # logger.info('Track %s remove from playlist' % track['file'])

@mpd_connect
def get_prev_track(client, degree=1):
    playlistinfo = client.playlistinfo()
    currentsong = client.currentsong()
    if playlistinfo and currentsong and (int(currentsong['pos'])-degree) >= 0:
        return [s for s in playlistinfo if int(s['pos']) == int(currentsong['pos'])-degree][0]

@mpd_connect
def get_next_track(client, degree=1):
    currentsong = client.currentsong()
    playlistinfo = client.playlistinfo()
    if not currentsong or not playlistinfo:
        return
    pos = int(currentsong['pos'])
    prev, next_ = [], []
    for track in playlistinfo:
        if int(track['pos']) < pos:
            prev.append(track)
        else:
            next_.append(track)
    newplaylistinfo = next_+prev
    if newplaylistinfo:
        return newplaylistinfo[degree]



