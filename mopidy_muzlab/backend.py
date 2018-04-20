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
from .mpd_client import new_mpd_client, clear_playlist

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
        self._refresh_playlists_rate = ext_config['refresh_playlists_rate']
        self._refresh_playlists_timer = None
        self._playlist_lock = Lock()
        # do not run playlist refresh around library refresh
        self._refresh_threshold = self._refresh_playlists_rate * 0.3
        self.audio = MuzlabAudio(config)
        self.playback = backend.PlaybackProvider(audio, self)
        self.playlists = MuzlabPlaylistsProvider(self, config)
        self._observer_rate = 5
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
        pass
        # with self._observer_lock:
        #     t0 = round(time.time())
        #     logger.info('Start observer')
        #     last_playlist = self.playlists.last_playlist
        #     exists, not_exists = self.playlists.check_playlist_files(last_playlist)
        #     if not_exists:
        #         self.playlists.sync_tracks(not_exists[:2])
        #         exists, not_exists = self.playlists.check_playlist_files(last_playlist)
        #     self.playlists.create_playlist_file(exists)
        #     client = new_mpd_client()
        #     clear_playlist(client)
        #     try:
        #         client.load('main')
        #     except Exception as es:
        #         return logger.error(es)
        #     t = round(time.time()) - t0
        #     logger.info('End observer %s' % t)


    def load_playlist(self):
        pass

    def _refresh_playlists(self):
        # logger.info(self.client.get_status())
        with self._playlist_lock:
            t0 = round(time.time())
            logger.info('Start refreshing playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing playlists in %ds', t)
