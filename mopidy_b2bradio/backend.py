from __future__ import unicode_literals

import logging
import time

from threading import Lock

from mopidy import backend

import pykka

from .playlists import B2bradioPlaylistsProvider
from .repeating_timer import RepeatingTimer

logger = logging.getLogger(__name__)


class B2bradioBackend(
        pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['b2bradio']

    def __init__(self, config, audio):
        super(B2bradioBackend, self).__init__()

        self.config = config
        self._refresh_playlists_rate = 6.0
        self._refresh_playlists_timer = None
        self._playlist_lock = Lock()
        # do not run playlist refresh around library refresh
        self._refresh_threshold = self._refresh_playlists_rate * 0.3
        self.playlists = B2bradioPlaylistsProvider(self, config)

    def on_start(self):
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

    def _refresh_playlists(self):
        with self._playlist_lock:
            t0 = round(time.time())
            logger.info('Start refreshing playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing playlists in %ds', t)
