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
def config_mock(tmpdir):
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
def entries_mock(playlist_mock):
    entries_mock = get_entries(playlist_mock)
    return entries_mock

@pytest.fixture
def playlist_mock():
    infile = open('playlists/last_playlist.m3u', 'r')
    playlist_mock = infile.readlines()
    playlist_mock = [line for line in playlist_mock if line and line != '\n']
    return playlist_mock

@pytest.fixture
def fake_entries_mock():
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
def backend_mock(config_mock):
    backend_mock = mock.Mock(spec=MuzlabBackend)
    backend_mock._config = config_mock
    return backend_mock

@pytest.fixture
def frontend_mock(config_mock):
    frontend_mock = mock.Mock(spec=MuzlabCoreEvent)
    frontend_mock._config = config_mock
    return frontend_mock

@pytest.fixture
def provider_mock(backend_mock, config_mock, entries_mock):
    provider_mock = MuzlabPlaylistsProvider(backend_mock, config_mock)
    tracks = [Track(uri=track[1], name=track[0]) for track in entries_mock]
    playlist = {'m3u:last_playlist.m3u':Playlist(uri='m3u:last_playlist.m3u', name='last_playlist', tracks=tracks)}
    provider_mock._playlist = playlist
    return provider_mock

