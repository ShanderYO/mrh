import os
import sys
import shlex
import logging
import subprocess
import datetime as dt
import socket
import re
from subprocess import call

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

def get_file_name(e):
	return e[1].replace('\n', '')

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


