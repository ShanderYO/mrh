# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import time
from threading import Lock
from datetime import datetime as dt
from mopidy import core, audio
import pykka
from .mpd_client import new_mpd_client, load_playlist, get_prev_track, get_next_track
from .playlists import get_crossfade_file_path
from .crossfade import Crossfade
from .repeating_timer import RepeatingTimer
from .utils import get_duration

logger = logging.getLogger(__name__)

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

    def gstreamer_error(self, error_msg, debug_msg):
        logger.info('Streamer Error %s : %s' % (error_msg, debug_msg))

    def playback_state_changed(self, old_state, new_state):
        client = new_mpd_client()
        playlist = client.playlistinfo()
        if len(playlist) == 0 or client.status()['state'] == 'stop':
            load_playlist(client)       
            client.play()
        logger.info('Playback changed: %s %s' % (old_state, new_state))

    def playlists_loaded(self):
        logger.info('Playlists loaded!!!')

    def track_playback_ended(self, tl_track, tl_previous, time_position):
        client = new_mpd_client()
        prev = get_prev_track(client, 2)
        if prev:
            path = prev['file'].replace('file://', '')
            logger.info('Remove: %s' % path)
            try:
                os.remove(path)
            except OSError:
                pass

    def track_playback_started(self, tl_track, tl_second_track):
        logger.info('Start: %s %s' % (tl_track.track.name, tl_track.track.uri))
        if self._crossfade:
            client = new_mpd_client()
            for i in range(1, 4):
                next_ = get_next_track(client, 4)
                if  next_:
                    cross_file = next_['file'].replace('file://', '')
                    current = '%s.mp3' % cross_file.split('/')[-1][:12]
                    second = cross_file.split('/')[-1][12:]
                    try:
                        duration = int(next_['title'].split('duration=')[1].split(',')[0])
                    except IndexError:
                        duration = get_duration('/home/files/%s/%s/%s/%s' %(current[0:3], current[3:6], current[6:9], current))
                    if not os.path.exists(cross_file):
                        crossfade = Crossfade(track=current, next_=second, track_duration=duration)
                        crossfade.add_crossfade()

