# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import time

from threading import Lock

from mopidy import backend

import pykka

from .playlists import MuzlabPlaylistsProvider
from .repeating_timer import RepeatingTimer

from .mpd_client import MPD

logger = logging.getLogger(__name__)


class MuzlabBackend(
        pykka.ThreadingActor, backend.Backend):
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
        self.playlists = MuzlabPlaylistsProvider(self, config)
        self.client = MPD.client

    def on_start(self):
        logger.info('Start mopidy!!!')
        self.playlists.refresh()
        # schedule playlist refresh as desired
        if self._refresh_playlists_rate > 0:
            self._refresh_playlists_timer = RepeatingTimer(
                self._refresh_playlists,
                self._refresh_playlists_rate)
            self._refresh_playlists_timer.start()

    def on_stop(self):
        if self._refresh_playlists_timer:
            self._refresh_playlists_timer.cancel()
            self._refresh_playlists_timer = None

    def load_playlist(self):
        pass

    def _refresh_playlists(self):
        # logger.info(self.client.get_status())
        with self._playlist_lock:
            t0 = round(time.time())
            # logger.info('Start refreshing playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            # logger.info('Finished refreshing playlists in %ds', t)
