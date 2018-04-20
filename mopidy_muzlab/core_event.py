# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import time
from threading import Lock
from datetime import datetime as dt
from mopidy import core, audio
import pykka
from .mpd_client import new_mpd_client, clear_playlist
from .playlists import get_correct_playlist, get_next, get_crossfade_file_path
from .crossfade import Crossfade
from .repeating_timer import RepeatingTimer

logger = logging.getLogger(__name__)


class Track():
    
    def __init__(self, id, title, artist, playtime, pos):
        self.id = id
        self.artist = artist
        self.title = title
        self.playtime = playtime
        self.pos = pos


def playlistinfo_objects(plinfo):
    playlist=[]
    for p in plinfo:
        line=p['title'].decode('UTF-8').strip()
        artist = line.split('artist=')[1].split(',')[0]
        title = line.split('title=')[1].split(',')[0]
        playtime = dt.strptime(line.split('start-time=')[1].split(',')[0], '%d %m %Y %H %M %S')
        track=Track(p['id'],artist,title,playtime,p['pos'])
        playlist.append(track)
    return playlist

def get_current_track(playlist, current_datetime):
    for track in playlist:
        if track.playtime < current_datetime:
            continue
        return track


class MuzlabCoreEvent(pykka.ThreadingActor, core.CoreListener):
    
    def __init__(self, config, core):
        super(MuzlabCoreEvent, self).__init__()
        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._playlist = ext_config['playlist']
        self._crossfade = ext_config['crossfade']
        self._observer_rate = 1
        self._observer_lock = Lock()
        self.core = core

    def on_start(self):
        logger.info('Start core!!!')
        if self._observer_rate > 0:
            self._observer_timer = RepeatingTimer(
                self._observer,
                self._observer_rate)
            self._observer_timer.start()

    def on_stop(self):
        if self._observer_timer:
            self._observer_timer.cancel()
            self._observer_timer = None

    def _observer(self):
        # logger.info(self.client.get_status())
        with self._observer_lock:
            t = round(time.time())
            # logger.info('Start observer %s' % str(t))

    # def track_playback_ended(self, tl_track, tl_previous, time_position):
    #     if self._crossfade and tl_previous:
    #         previous = tl_previous.track.uri.replace('file://', '')
    #         logger.info('Remove: %s' % previous)
    #         try:
    #             os.remove(previous)
    #         except OSError:
    #             pass

    def tracklist_changed(self):
        pass

    def gstreamer_error(self, error_msg, debug_msg):
        logger.info('Streamer Error %s : %s' % (error_msg, debug_msg))
        # client = new_mpd_client()        
        # client.next()

    def get_playlist(self, uri):
        return self.core.playlists.lookup(uri).get()

    def load_playlist(self, playlist, playlist_slice=slice(0, None)):
        self.core.tracklist.add(playlist.tracks[playlist_slice]).get()

    def playback_state_changed(self, old_state, new_state):
        client = new_mpd_client()
        playlist = client.playlistinfo()
        if len(playlist) == 0 or client.status()['state'] == 'stop':
            clear_playlist(client)
            client.load(get_correct_playlist(self._playlist))            
            client.play()
        logger.info('Playback changed: %s %s' % (old_state, new_state))

    def playlists_loaded(self):
        logger.info('Playlists loaded!!!')

    def track_playback_started(self, tl_track, tl_second_track):
        logger.info('Start: %s' % (tl_track.track.name))
    #     if self._crossfade and tl_second_track:
    #         cross_file = tl_second_track.track.uri.replace('file://', '')
    #         print(cross_file)
    #         current = '%s.mp3' % cross_file.split('/')[-1][:12]
    #         second = cross_file.split('/')[-1][12:]
    #         print(current, second)
    #         duration = int(tl_second_track.track.name.split('duration=')[1].split(',')[0])
    #         if not os.path.exists(cross_file):
    #             crossfade = Crossfade(track=current, next_=second, track_duration=duration)
    #             crossfade.add_crossfade()


        # current_playtime = dt.strptime(tl_track.track.name.split('start-time=')[1].split(',')[0], '%d %m %Y %H %M %S')
        # dt_now = dt.now()
        # distance = (dt_now - current_playtime).total_seconds()
        # logger.info('distance = %s' % (distance))
        # if distance > 300:
        #     client = new_mpd_client()
        #     playlistinfo = playlistinfo_objects(client.playlistinfo())
        #     current_track = get_current_track(playlistinfo, dt_now)
        #     if current_track:
        #         client.play(current_track.pos)
        #         logger.info('Synhr play %s %s' % (current_track.id, current_track.title))

