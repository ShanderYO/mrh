# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import time
from threading import Lock
from mopidy import backend
from mopidy.audio import Audio
import pykka
from .playlists import MuzlabPlaylistsProvider
from .repeating_timer import RepeatingTimer
from .mpd_client import new_mpd_client, load_playlist

logger = logging.getLogger(__name__)


class MuzlabAudio(Audio):
    def __init__(self, config):
        super(MuzlabAudio, self).__init__(config, None)
        ext_config = config['muzlab']


class MuzlabBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['muzlab']

    def __init__(self, config, audio):
        super(MuzlabBackend, self).__init__()

        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._refresh_playlists_rate = 300
        self._refresh_playlists_timer = None
        self._playlist_lock = Lock()
        self.audio = MuzlabAudio(config)
        self.playback = backend.PlaybackProvider(audio, self)
        self.playlists = MuzlabPlaylistsProvider(self, config)
        self._observer_rate = 10
        self._observer_lock = Lock()

    def on_start(self):
        logger.info('Start backend!!!')
        if self._refresh_playlists_rate > 0:
            self._refresh_playlists_timer = RepeatingTimer(
                self._refresh_playlists,
                self._refresh_playlists_rate)
            self._refresh_playlists_timer.start()
        if self._observer_rate > 0:
            self._observer_timer = RepeatingTimer(
                self._observer,
                self._observer_rate)
            self._observer_timer.start()

    def on_stop(self):
        if self._refresh_playlists_timer:
            self._refresh_playlists_timer.cancel()
            self._refresh_playlists_timer = None
        if self._observer_timer:
            self._observer_timer.cancel()
            self._observer_timer = None

    def _observer(self):
        with self._observer_lock:
            try:
                pos = self.playback.get_time_position()
                time.sleep(0.2)
                pos_ = self.playback.get_time_position()
                if pos != pos_:
                    return
                client = new_mpd_client()
                client.play()
                time.sleep(0.2)
                pos__ = self.playback.get_time_position()
                if pos_ != pos__:
                    return
                load_playlist(client)
                client.play()
            except Exception as es:
                logger.info(str(es))


    def _refresh_playlists(self):
        with self._playlist_lock:
            t0 = round(time.time())
            logger.info('Start refreshing playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing playlists in %ds', t)
