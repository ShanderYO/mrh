from __future__ import unicode_literals

import logging
import os
from datetime import datetime as dt
from mopidy import core, listener
import pykka
from mpd import MPDClient

logger = logging.getLogger(__name__)


class Track():
    def __init__(self, id, title, artist, playtime):
        self.id = id
        self.artist = artist
        self.title = title
        self.playtime = playtime

def parsem3u(infile):
    try:
        assert(type(infile) == '_io.TextIOWrapper')
    except AssertionError:
        infile = open(infile,'r')

    line = infile.readline()
    if not line.startswith('#EXTM3U'):
       return

    # initialize playlist variables before reading file
    playlist=[]
    id = 0
    for line in infile:
        line=line.decode('UTF-8').strip()
        if line.startswith('#EXTINF:'):
            artist = line.split('artist=')[1].split(',')[0]
            title = line.split('title=')[1].split(',')[0]
            playtime = dt.strptime(line.split('start-time=')[1].split(',')[0], '%d %m %Y %H %M %S')
            song=Track(id,artist,title,playtime)
            playlist.append(song)
            id += 1
            # reset the song variable so it doesn't use the same EXTINF more than once
    infile.close()
    return playlist


def get_current_track(playlist, current_datetime):
	for track in playlist:
		if track.playtime < current_datetime:
			continue
		return track


class B2bradioCoreEvent(pykka.ThreadingActor, core.CoreListener):
    def __init__(self, config, core):
        super(B2bradioCoreEvent, self).__init__()
        ext_config = config['b2bradio']
        self._playlists_dir = ext_config['playlists_dir']
        self._playlist = parsem3u(os.path.join(self._playlists_dir,'main.m3u'))

    def track_playback_ended(self, tl_track, time_position):
    	pass

	def tracklist_changed(self):
		pass

    def playlists_loaded(self):
        logger.info('Playlists_loaded!!!')

    def track_playback_started(self, tl_track):
    	logger.info('Start %s' % (tl_track.track.name))
        client = MPDClient()
        client.connect("localhost", 6600)
        current_playtime = dt.strptime(tl_track.track.name.split('start-time=')[1].split(',')[0], '%d %m %Y %H %M %S')
        dt_now = dt.now()
    	distance = abs((current_playtime - dt_now).total_seconds())
    	logger.info('distance = %s' % (distance))
    	if distance > 600:
    		current_track = get_current_track(self._playlist, dt_now)
    		if current_track:
    			client.play(current_track.id)
    			logger.info('Synhr play %s %s' % (current_track.id, current_track.title))
		
