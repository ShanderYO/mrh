from __future__ import unicode_literals

import logging

from mopidy import core, listener

import pykka

from mpd import MPDClient

logger = logging.getLogger(__name__)


class B2bradioCoreEvent(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(B2bradioCoreEvent, self).__init__()

    def track_playback_ended(self, tl_track, time_position):
        client = MPDClient()
        client.connect("localhost", 6600)
        current = client.currentsong()
        logger.info('track_playback_ended {}, {} '.format(str(current['id']), current['title']))