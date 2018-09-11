from __future__ import unicode_literals

import logging
import os
import time
import subprocess
import pykka
import mock
import pytest
from threading import Lock
from mopidy.models import Playlist, Ref, Track
from mopidy_muzlab.utils import get_entries
from mopidy_muzlab.backend import MuzlabAudio, MuzlabBackend
from mopidy_muzlab.playlists import MuzlabPlaylistsProvider
from mopidy_muzlab.core_event import MuzlabCoreEvent
from mopidy_muzlab.repeating_timer import RepeatingTimer
from mopidy_muzlab.mpd_client import new_mpd_client, load_playlist
from faker import Faker

@pytest.fixture
def fake_config(tmpdir):
    return {
        'core': {
            'cache_dir': '%s' % tmpdir.join('cache'),
            'data_dir': '%s' % tmpdir.join('data'),
        },
        'muzlab': {
            'enabled': True,
            'default_encoding': 'latin-1',
            'playlist_url': 'http://muz-lab.ru/api/v1/stream/playlist_box',
            'refresh_playlists_rate': 900,
            'playlists_dir': 'playlists',
            'crossfade': False,
            'video_control': False,
            'base_dir': None,
            'playlist': None,
            'default_extension': '.m3u',
        },
        'm3u': {
			'enabled': True,
			'default_encoding': 'latin-1',
			'default_extension': '.m3u',
			'base_dir': 'playlists',
			'playlists_dir': 'playlists',
		},
    }


@pytest.fixture
def start_tracks_log_path():
    return 'playlists/start_tracks.log'

@pytest.fixture
def playlist():
    infile = open('playlists/last_playlist.m3u', 'r')
    playlist = infile.readlines()
    playlist = [line for line in playlist if line and line != '\n']
    return playlist

@pytest.fixture
def entries(playlist):
    entries = get_entries(playlist)
    return entries

@pytest.fixture
def fake_start_tracks(start_tracks_log_path):
    infile = open(start_tracks_log_path, 'r')
    result = infile.readlines()
    result = [line for line in result if line and line != '\n' and 'Start' in line and 'rotation_id=' in line]
    return result

@pytest.fixture
def fake_last_start_id(fake_start_tracks):
    last = fake_start_tracks[-1]
    return int(last.split('rotation_id=')[1].split(',')[0])

@pytest.fixture
def fake_played(fake_start_tracks):
    played = []
    for line in fake_start_tracks:
        if line and line != '\n' and 'Start' in line and 'rotation_id=' in line:
            played.append(int(line.split('rotation_id=')[1].split(',')[0]))

@pytest.fixture
def fake_entries():
    faker = Faker()
    entries = []
    for i in range(300):
        start_date = faker.date_time_this_month().strftime('%d %m %Y %H %M %S')
        duration = faker.random.randint(0,1000000000)
        size = faker.random.randint(0,1000000000)
        media_id = faker.random.randint(0,1000000000)
        rotation_id = faker.random.randint(0,1000000000)
        type = faker.random.randint(0,1)
        meta = 'start-time=%s,duration=%s,size=%s,media_id=%s,rotation_id=%s,type=%s' % (start_date, duration, size, media_id, rotation_id, type)
        lamb = lambda: faker.pystr(min_chars=3, max_chars=3).lower()
        p1,p2,p3,p4 = lamb(), lamb(), lamb(), lamb()
        path = 'file:///home/files/%s/%s/%s/%s' % (p1,p2,p3,p1+p2+p3+p4+'.mp3')
        entry = (meta, path)
        entries.append(entry)
    return entries

@pytest.fixture
def fake_backend(fake_config):
    backend = mock.Mock(spec=MuzlabBackend)
    backend._config = fake_config
    return backend

@pytest.fixture
def fake_frontend(fake_config):
    frontend = mock.Mock(spec=MuzlabCoreEvent)
    frontend._config = fake_config
    return frontend

@pytest.fixture
def fake_provider(fake_backend, fake_config, entries):
    provider = MuzlabPlaylistsProvider(fake_backend, fake_config)
    tracks = [Track(uri=track[1], name=track[0]) for track in entries]
    playlist = {'m3u:last_playlist.m3u':Playlist(uri='m3u:last_playlist.m3u', name='last_playlist', tracks=tracks)}
    provider._playlist = playlist
    return provider

