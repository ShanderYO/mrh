# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from os import remove
from os.path import isfile
from datetime import datetime as dt
from mopidy import core
import pykka
from .mpd_client import new_mpd_client, load_playlist, get_prev_track, get_next_track
from .crossfade import Crossfade
from .repeating_timer import RepeatingTimer
from .utils import get_duration, add_row_to_file, send_states, get_musicbox_id, get_rotation_id

logger = logging.getLogger(__name__)

class MuzlabCoreEvent(pykka.ThreadingActor, core.CoreListener):
    
    def __init__(self, config, core):
        super(MuzlabCoreEvent, self).__init__()
        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._playlist = ext_config['playlist']
        self._crossfade = ext_config['crossfade']
        self._start_tracks_log = ext_config['start_tracks_log']
        self._state_uri = 'https://muz-lab.ru/api/v1/stream/musicbox/%s/send_states/' % get_musicbox_id()
        self.core = core

    def gstreamer_error(self, error_msg, debug_msg):
        logger.info('Streamer Error %s : %s' % (error_msg, debug_msg))

    def playlists_loaded(self):
        logger.info('Playlists loaded!!!')

    def track_playback_ended(self, tl_track, tl_previous, time_position):
        if self._crossfade:
            prev = get_prev_track(degree=2)
            if prev:
                path = prev['file'].replace('file://', '')
                logger.info('Remove: %s' % path)
                try:
                    remove(path)
                except OSError:
                    pass

    def track_playback_started(self, tl_track, tl_second_track):
        try:
            name = tl_track.track.name.decode('utf-8')
        except UnicodeEncodeError:
            logger.error('Can t decode track title. Track will be skipped')
            self.core.playback.next()
            return
        try:
            uri = tl_track.track.uri.decode('utf-8')
        except UnicodeEncodeError:
            logger.error('Can t decode track uri. Track will be skipped')
            self.core.playback.next()
            return
        start = '%s - Start: %s %s' % (dt.now().strftime('%Y-%m-%d %H:%M:%S'), name, uri)
        current_rotation = get_rotation_id(name)
        logger.info(start)
        add_row_to_file(start, self._start_tracks_log)
        send_states(self._state_uri, dict(current_rotation=current_rotation))
        if self._crossfade:
            for i in range(1, 4):
                next_ = get_next_track(i)
                if not next_:
                    return
                cross_file = next_['file'].replace('file://', '')
                if isfile(cross_file):
                    return
                current = '%s.mp3' % cross_file.split('/')[-1][:12]
                current = '/home/files/%s/%s/%s/%s' %(current[0:3], current[3:6], current[6:9], current)
                second = cross_file.split('/')[-1][12:]
                second = '/home/files/%s/%s/%s/%s' %(second[0:3], second[3:6], second[6:9], second)
                if not isfile(current) or not isfile(second):
                    return
                try:
                    duration = int(next_['title'].decode('utf-8').split('duration=')[1].split(',')[0])
                except (IndexError, ValueError, TypeError):
                    duration = None
                crossfade = Crossfade(track=current, next_=second, track_duration=duration)
                crossfade.add_crossfade()

