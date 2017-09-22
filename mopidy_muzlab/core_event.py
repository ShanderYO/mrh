# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
from datetime import datetime as dt
from mopidy import core, audio
import pykka
from .mpd_client import new_mpd_client
from .playlists import get_correct_playlist

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


class MuzlabCoreEvent(pykka.ThreadingActor, core.CoreListener, audio.AudioListener):
    
    def __init__(self, config, core):
        super(MuzlabCoreEvent, self).__init__()
        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._playlist = ext_config['playlist']

    def track_playback_ended(self, tl_track, time_position):
    	pass

	def tracklist_changed(self):
		pass

    def playback_state_changed(self, old_state, new_state):
        client = new_mpd_client()
        playlist = client.playlistinfo()
        if len(playlist) == 0 or client.status()['state'] == 'stop':
            client.clear()
            client.load(get_correct_playlist(self._playlist))            
            client.play()
        logger.info('Playback changed: %s %s' % (old_state, new_state))

    def playlists_loaded(self):
        logger.info('Playlists loaded!!!')

    def position_changed(self, position):
        logger.info('position_changed!!! %s' % str(position))

    def track_playback_started(self, tl_track):
        from datetime import datetime as dt
    	logger.info('Start: %s' % (tl_track.track.name))
        current_playtime = dt.strptime(tl_track.track.name.split('start-time=')[1].split(',')[0], '%d %m %Y %H %M %S')
        dt_now = dt.now()
    	distance = (dt_now - current_playtime).total_seconds()
    	logger.info('distance = %s' % (distance))
    	if distance > 300:
            client = new_mpd_client()
            playlistinfo = playlistinfo_objects(client.playlistinfo())
            current_track = get_current_track(playlistinfo, dt_now)
            if current_track:
                client.play(current_track.pos)
                logger.info('Synhr play %s %s' % (current_track.id, current_track.title))