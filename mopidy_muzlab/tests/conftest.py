from __future__ import unicode_literals

import logging
import os
import time
import subprocess
import pykka
import mock
import pytest
from threading import Lock
from mopidy_muzlab.utils import get_entries
from mopidy_muzlab.backend import MuzlabAudio, MuzlabBackend
from mopidy_muzlab.playlists import MuzlabPlaylistsProvider
from mopidy_muzlab.repeating_timer import RepeatingTimer
from mopidy_muzlab.mpd_client import new_mpd_client, load_playlist

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
            'playlists_dir': '/home/mopidy/mopidy/playlists',
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
			'base_dir': '/home/mopidy/mopidy/playlists',
			'playlists_dir': '/home/mopidy/mopidy/playlists',
		},
    }

@pytest.fixture
def entryes_mock(playlist_mock):
    entries = get_entries(playlist_mock)
    return entries

@pytest.fixture
def playlist_mock(tmpdir):
    infile = open('/home/mopidy/mopidy/playlists/last_playlist.m3u', 'r')
    readlines = infile.readlines()
    readlines = [line for line in readlines if line and line != '\n']
    return readlines

@pytest.fixture
def backend_mock(config_mock):
    backend_mock = mock.Mock(spec=MuzlabBackend)
    backend_mock._config = config_mock
    return backend_mock

@pytest.fixture
def provider_mock(backend_mock, config_mock):
    return MuzlabPlaylistsProvider(backend_mock, config_mock)

