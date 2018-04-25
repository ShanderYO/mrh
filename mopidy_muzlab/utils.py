import logging
import subprocess
import datetime as dt

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



