from __future__ import unicode_literals
import pytest
from mopidy import backend as backend_api

def test_playlist_exists(playlist):
	exists = False
	if len(playlist):
		exists = True
	assert exists

def test_playlist_format(playlist):
	playlist = playlist[2:]
	assert all(entry.decode('utf-8').startswith('#EXTINF') for n,entry in enumerate(playlist) 
																	if entry and n%2==0 and entry != '\n')
def test_playlist_length(entries):
	assert entries > 500

def test_is_a_playlists_provider(fake_provider):
    assert isinstance(fake_provider, backend_api.PlaylistsProvider)

def test_get_items(fake_provider):
	assert fake_provider.get_items('m3u:last_playlist.m3u')

def test_create(fake_provider):
	assert fake_provider.create('boo')

def test_lookup_valid(fake_provider):
	assert fake_provider.lookup('m3u:boo.m3u')

def test_lookup_invalid(fake_provider):
	fake_provider.delete('m3u:boo.m3u')









