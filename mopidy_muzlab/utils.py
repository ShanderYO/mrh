import os
import fnmatch
import sys
import shlex
import logging
import subprocess
import datetime as dt
import socket
import re
from subprocess import call
from multiprocessing.dummy import Pool as ThreadPool

logger = logging.getLogger(__name__)

def concatenate_filename(file1, file2):
	cut_ext = lambda s: s.split('/')[-1].replace('\n', '').replace('.mp3', '')
	return '%s%s.mp3' % (cut_ext(file1), cut_ext(file2))

def get_duration(track):
	result = subprocess.Popen(["ffprobe", track],
		stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
	lines = [x for x in result.stdout.readlines() if 'Duration' in x]
	if lines:
		try:
			line = lines[0].split(',')[0].split('Duration: ')[1]
		except KeyError:
			return
		try:
			data = dt.datetime.strptime(line,'%H:%m:%S.%f')
			data = tuple(int(i) for i in data.strftime('%H %m %S %f').split())
			duration = int(dt.timedelta(hours=data[0], minutes=data[1], 
										seconds=data[2], microseconds=data[3]).total_seconds()*1000)
		except ValueError:
			return
		return duration

def get_file_name(entry):
	return entry[1].replace('\n', '')

def get_musicbox_id():
	return re.sub(r'[\D]+', r'', socket.gethostname())

def probe_file(filename):
    cmnd = ['ffprobe', '-show_format', '-pretty', '-loglevel', 'quiet', filename]
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err =  p.communicate()
    if err:
    	return logger.warning('File: %s not valid audio file; Error: %s' % (filename, err))
    if 'format_name=mp3' in out and 'bit_rate' in out:
		return True
    logger.warning('File: %s not valid audio file; Error: %s' % (filename, err))

def check_header(filename):
    cmnd = ['file', filename]
    p = subprocess.Popen(cmnd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err =  p.communicate()
    if err:
    	return logger.warning('File: %s not valid audio file; Error: %s' % (filename, err))
    if 'Audio' in out:
		return True
    logger.warning('File: %s not valid audio file; Error: %s' % (filename, err))

def get_crossfade_file_path(path, next_path, crossfade_directory='/tmp/crossfade'):
    return '%s/%s' % (crossfade_directory, concatenate_filename(path, next_path))

def check_crossfade_file(entry, entry_next):
	cross_file = get_crossfade_file_path(entry[1].decode('utf-8').replace('\n', ''), 
            entry_next[1].decode('utf-8').replace('\n', ''))
	if not os.path.exists(cross_file):
		return
	return True

def check_entry(entry):
    if (entry[0].decode('utf-8').startswith('#EXTINF') 
            and entry[1].decode('utf-8').endswith('mp3')):
        return True

def get_entries(readlines):
	entries = tuple((readlines[n+1], get_file_name([None, file_])) for 
						n, file_ in enumerate(readlines[2:]) if n % 2 != 0)
	return tuple(entry for entry in entries if check_entry(entry))

def exists_files():
    files = []
    for root, dirnames, filenames in os.walk('/home/files/'):
        for filename in fnmatch.filter(filenames, '*.mp3'):
            files.append(os.path.join(root, filename))
    if not files:
        return []
    result = [file for file in files if file]
    return result

def check_files_async(entryes, checked=[]):
	def check_file(entry):
		if entry[1] in checked:
			return entry
		try:
			size = entry[0].split('size=')[1].split(',')[0]
		except:
			size = None
		if (not os.path.exists(entry[1]) or
			os.stat(entry[1]).st_size != long(size)):
			try:
				os.remove(entry[1])
			except OSError:
				pass
			return []
		return entry

	results = map(check_file, entryes)
	# pool = ThreadPool(4)
	# results = pool.map(check_file, entryes)
	# pool.close()
	# pool.join()
	return tuple(entry for entry in results if entry)



