# -*- coding: utf-8 -*-
import socket
from os.path import isfile
from mpd import MPDClient, CommandError
from .repeating_timer import RepeatingTimer
import time
import logging
from collections import deque
mpd_host = '127.0.0.1'
mpd_port = 6600

logger = logging.getLogger(__name__)

def new_mpd_client():
    client = MPDClient()
    client.timeout = 180
    client.idletimeout = 240
    c = 0
    while True:
        try:
            client.connect(mpd_host, mpd_port)
            client.currentsong()
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
        try:
            i = int(status['song']) + 2
        except KeyError:
            break
        try:
            client.delete(i)
        except CommandError:
            break

def load_playlist(client, playlist='main'):
    clear_playlist(client)
    client.load(playlist)
    clear_replays(client)

def clear_replays(client):
    '''
        Remove repitead track from playlist
    '''
    status = client.status()
    try:
        pos = int(status['song'])
    except KeyError:
        return
    playlist = client.playlistinfo()
    played = get_played_files()
    will_play = []
    for entry in client.playlistinfo():
        if int(entry['pos']) > pos:
            will_play.append(entry)
    for entry in will_play[:100]:
        if entry['file'].split('/')[-1][12:] in played[-100:]:
            client.deleteid(int(entry['id']))

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

def get_played_files(log_file='/home/mopidy/mopidy/start_tracks.log'):
    if not isfile(log_file):
        open(log_file, 'a')
    with open(log_file, 'r') as f:
        readlines = f.readlines()
        played = []
        for n, line in enumerate(readlines):
            if 'Start:' in line and 'file://' in line:
                played.append(line.replace('\n', '').split('file://')[1])
        return list(set(played))

def get_last_start_id(log_file='/home/mopidy/mopidy/start_tracks.log'):
    if not isfile(log_file):
        open(log_file, 'a')
    with open(log_file, 'r') as f:
        readlines = f.readlines()
        if not readlines:
            return
        line = readlines[-1]
        if 'Start:' in line and 'rotation_id=' in line:
            try:
                return int(line.replace('\n', '').split('rotation_id=')[1].split(',')[0])
            except (IndexError, ValueError):
                pass

def get_next_load_tracks(tracks):
    next_load_tracks = None
    last_id = get_last_start_id()
    if last_id:
        last_track = tuple(n for n, track in enumerate(tracks) if 'rotation_id=%s' % str(last_id) in track[0])
        if last_track:
            last_track_key = last_track[0]
            next_load_tracks = tracks[last_track_key+1:] + tracks[:last_track_key+1]
    else:
        next_load_tracks = tuple(track for track in tracks if track[1])
    if not next_load_tracks:
        next_load_tracks = tracks
    return next_load_tracks

def get_prev_track(client, degree=1):
    playlistinfo = client.playlistinfo()
    currentsong = client.currentsong()
    if playlistinfo and currentsong and (int(currentsong['pos'])-degree) >= 0:
        return [s for s in playlistinfo if int(s['pos']) == int(currentsong['pos'])-degree][0]

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



