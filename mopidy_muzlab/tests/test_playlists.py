from __future__ import unicode_literals
import pytest
from mopidy import backend as backend_api

def test_playlist_exists(playlist_mock):
	exists = False
	if len(playlist_mock):
		exists = True
	assert exists

def test_playlist_format(playlist_mock):
	playlist_mock = playlist_mock[2:]
	assert all(entry.decode('utf-8').startswith('#EXTINF') for n,entry in enumerate(playlist_mock) 
																	if entry and n%2==0 and entry != '\n')
def test_playlist_length(entries_mock):
	assert entries_mock > 500

def test_is_a_playlists_provider(provider_mock):
    assert isinstance(provider_mock, backend_api.PlaylistsProvider)

def test_get_items(provider_mock):
	assert provider_mock.get_items('m3u:last_playlist.m3u')

def test_create(provider_mock):
	assert provider_mock.create('boo')

def test_lookup_valid(provider_mock):
	assert provider_mock.lookup('m3u:boo.m3u')

def test_lookup_invalid(provider_mock):
	provider_mock.delete('m3u:boo.m3u')









