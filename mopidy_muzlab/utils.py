from os import stat, walk, remove
from os.path import isfile, join
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

def get_rotation_id(line):
    if 'rotation_id' not in line:
        return 0
    rotation_id = line.replace('\n', '').split('rotation_id=')[1].split(',')[0]
    return int(rotation_id)

def get_played_rotation(log_file='/home/mopidy/mopidy/start_tracks.log'):
    if not isfile(log_file):
        open(log_file, 'a')
    with open(log_file, 'r') as f:
        readlines = f.readlines()
        played = []
        for n, line in enumerate(readlines):
            if 'Start:' in line and 'rotation_id' in line and 'file://' in line:
                played.append(line.replace('\n', ''))
        return list(set([get_rotation_id(pl) for pl in played]))

def get_last_start_id(log_file='/home/mopidy/mopidy/start_tracks.log'):
    if not isfile(log_file):
        open(log_file, 'a')
    with open(log_file, 'r') as f:
        readlines = f.readlines()
        if not readlines:
            return
        line = readlines[-1]
        if 'Start:' in line and 'rotation_id=' in line:
            try:
                return get_rotation_id(line)
            except (IndexError, ValueError):
                pass

def get_next_load_tracks(tracks):
    next_load_tracks = None
    last_id = get_last_start_id()
    if last_id:
        last_track = tuple(n for n, track in enumerate(tracks) if 'rotation_id=%s' % str(last_id) in track[0])
        # logger.info('Last id: %s' % str(last_id))
        # logger.info('last_track: %s' % str(last_track))
        if last_track:
            last_track_key = last_track[0]
            next_load_tracks = tracks[last_track_key+1:] + tracks[:last_track_key+1]
    else:
        next_load_tracks = tuple(track for track in tracks if track[1] and track[0] and get_rotation_id(track[0]))
    if not next_load_tracks:
        next_load_tracks = tuple(track for track in tracks if track[1] and track[0] and get_rotation_id(track[0]))
    return next_load_tracks

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
	if not isfile(cross_file):
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
    for root, dirnames, filenames in walk('/home/files/'):
        for filename in fnmatch.filter(filenames, '*.mp3'):
            files.append(join(root, filename))
    if not files:
        return []
    result = [file for file in files if file]
    return result

def check_files_async(entryes, checked=[]):
	def check_file(entry):
		if entry[1] in checked:
			return entry
		if not isfile(entry[1]):
			return []
		if stat(entry[1]).st_size <= 1024*8 or not check_header(entry[1]):
			try:
				remove(entry[1])
			except OSError:
				pass
			return []
		return entry

	pool = ThreadPool(4)
	result = []
	for r in pool.imap(check_file, entryes, chunksize=1):
		if r:
			result.append(r)
		if len(result) >= 200:
			pool.terminate()
			break

	pool.close()
	pool.join()
	return tuple(entry for entry in result if entry)

def add_row_to_file(row, path):
	with open(path, 'ab+') as f:
		f.write('%s\n' % row)

def cut_file_rows_in_bot(path, numb=10000):
	if not isfile(path):
		open(path, 'a')
	infile = open(path, 'r')
	readlines = infile.readlines()
	readlines = readlines[-numb:]
	with open(path, 'wb') as f:
		for row in readlines:
			f.write(row)
	logger.info('Cut %s lines' % len(readlines))

def musicbox_request_header():
    import re,socket,hashlib

    MUSIC_BOX_API_SALT = "Ma'\}D@)EwQ\+b}&~Y=c@;^P;dH'`'X')HfSf{4RjE(wd#neVQ7Nv^QcHe[/!.u"

    with open('/proc/cpuinfo') as f:
        try:
            serial = [re.findall(r'\t:\s(.+?)\n', k)[0] for k in f.readlines() if 'Serial' in k][0]
        except IndexError:
            serial = ''

    md5 = hashlib.md5()
    md5.update((''.join([socket.gethostname(), serial, MUSIC_BOX_API_SALT])).encode())
    return {'musicbox-token': md5.hexdigest(), 'serial': serial}

def clear_replays(entryes, clear_number=30):
    '''
        Remove repitead track from playlist
    '''
    result = []
    played = get_played_rotation()
    for entry in entryes:
        id_ = get_rotation_id(entry[0])
        if id_ and id_ not in played[-clear_number:]:
            result.append(entry)
    return result








