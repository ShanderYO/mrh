from __future__ import unicode_literals
import os
from mopidy_muzlab.utils import check_files_async, check_header

def test_check_files_async(entries_mock):
	exists = check_files_async(entries_mock[:10])
	assert all(os.path.isfile(e[1]) and os.stat(e[1]).st_size >= 1024*8 and check_header(e[1]) for e in exists)