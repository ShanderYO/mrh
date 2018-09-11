from __future__ import unicode_literals
import os
from mopidy_muzlab.utils import (check_files_async, check_header, get_musicbox_id, get_next_load_tracks,
							clear_replays, get_rotation_id, get_played_rotation, get_last_start_id, check_header)

def test_check_files_async(entries):
	exists = check_files_async(entries[:10])
	assert all(os.path.isfile(e[1]) and os.stat(e[1]).st_size >= 1024*8 and check_header(e[1]) for e in exists)

def test_get_musicbox_id():
	try:
		m_id = int(get_musicbox_id())
	except TypeError:
		m_id = None
	assert m_id

def test_get_rotation_id(fake_entries):
	entries_number = len(fake_entries)
	rotations = [get_rotation_id(e[0]) for e in fake_entries]
	assert len(rotations) == entries_number and all(type(i) is int for i in rotations)

def test_get_played_rotation(start_tracks_log_path):
	played = get_played_rotation(log_file=start_tracks_log_path)
	assert played and type(played) is list and all(type(i) is int for i in played)

def test_get_last_start_id(fake_last_start_id, start_tracks_log_path):
	id_ = get_last_start_id(log_file=start_tracks_log_path)
	assert fake_last_start_id == id_

def test_get_next_load_tracks(entries, start_tracks_log_path):
	next_ = get_next_load_tracks(entries, log_file=start_tracks_log_path)
	assert next_ and type(next_) is tuple

# def test_check_header(entries):
# 	accepted = [e for e in entries[:10] if check_header(e[1])]
# 	assert len(accepted) == 10

def test_clear_replays(fake_entries, start_tracks_log_path):
	entries = fake_entries*2
	assert len(fake_entries) == len(clear_replays(entries, log_file=start_tracks_log_path))














