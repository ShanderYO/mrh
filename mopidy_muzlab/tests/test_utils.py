from __future__ import unicode_literals
import os
from mopidy_muzlab.utils import check_files_async, check_header, get_musicbox_id, get_rotation_id

def test_check_files_async(entries_mock):
	exists = check_files_async(entries_mock[:10])
	assert all(os.path.isfile(e[1]) and os.stat(e[1]).st_size >= 1024*8 and check_header(e[1]) for e in exists)

def test_get_musicbox_id(entries_mock):
	try:
		m_id = int(get_musicbox_id())
	except TypeError:
		m_id = None
	assert m_id

def test_get_rotation_id(fake_entries_mock):
	entries_number = len(fake_entries_mock)
	entries = [e for e in fake_entries_mock if get_rotation_id(e[0])]
	assert len(entries) == entries_number




