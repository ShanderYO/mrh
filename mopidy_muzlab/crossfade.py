import os
import subprocess
import time
import datetime as dt
import logging
from shutil import move, copy
from .utils import concatenate_filename
from .mpd_client import new_mpd_client
from .utils import get_duration

logger = logging.getLogger(__name__)

class Crossfade(object):

	def __init__(self, track, next_, crossfade=3.0, out_directory='/tmp/crossfade/', out_file=None,
						cut_start=True, track_duration=None, curve='qsin'):
		self.track = track.replace('\n', '')
		self.next_ = next_.replace('\n', '')
		self.cut_start = cut_start
		self.crossfade = crossfade
		self.track_duration = track_duration if track_duration else get_duration(self.track)
		self.out_directory = out_directory
		self.out_file = out_file if out_file else concatenate_filename(self.track, self.next_)
		self.curve = curve
		if not os.path.exists(os.path.dirname(out_directory)):
			os.makedirs(os.path.dirname(out_directory))
		self.output = '%s%s' % (out_directory, self.out_file)

	def add_crossfade(self):
		if os.path.exists(self.output):
			return
		elif not os.path.exists(self.track):
			return logger.error('Failed crossfade track %s does not exist' % track)
		elif not os.path.exists(self.next_):
			logger.info('Not crossfade beetwen %s and %s, %s does not exist' % (self.track, self.next_, self.next_))
			copy(self.track, self.output)
			return
		elif not self.track_duration:
			logger.info('Not crossfade beetwen %s and %s, failed duration' % (self.track, self.next_))
			copy(self.track, self.output)
			return
		chunk1, chunk2 = self.split_track()
		crossfile = self.add_crossfade_between_files()
		self.concatenate_chunk()
		# logger.info('cut: %s' % self.cut_start)
		if self.cut_start:
			self.cut()
		logger.info('Crossfade:%s' % self.output)
		for f in [chunk1, chunk2, crossfile, '%s.tmp' % self.output]:
			try:
				os.remove(f)
			except:
				pass
		# self.remove_old_file()
		return self.output

	def split_track(self):
		splitting = self.track_duration - (self.crossfade+1)
		chunk1 = '/tmp/%s' % self.track.split('/')[-1].replace('.mp3','.chunk1.mp3')
		chunk2 = '/tmp/%s' % self.track.split('/')[-1].replace('.mp3','.chunk2.mp3')
		command1 = 'ffmpeg -y -ss 0 -t %s -i %s -c copy %s' % (splitting, self.track, chunk1)
		command2 = 'ffmpeg -y -ss %s -i %s -c copy %s' % (splitting, self.track, chunk2)
		self.run(command1)
		self.run(command2)
		self.chunk1, self.chunk2 = chunk1, chunk2
		return [self.chunk1, self.chunk2]

	def cut(self):
		tmp = '%s.tmp' % self.output
		move(self.output, tmp)
		command = 'ffmpeg -y -ss %s -i %s -c copy %s' % (self.crossfade, tmp, self.output)
		self.run(command)
		
	def add_crossfade_between_files(self):
		crossfile = '/tmp/%s' % self.chunk2.split('/')[-1].replace('.chunk2.mp3', '.cross.mp3')
		filter_complex = '[1]atrim=0:4[b];[0][b]acrossfade=d=%s:c1=%s:c2=%s' % (self.crossfade, 
															self.curve, self.curve)
		command = 'ffmpeg -y -i %s -i %s -filter_complex %s %s' % (self.chunk2, 
									self.next_, filter_complex, crossfile)
		self.run(command)
		self.crossfile = crossfile
		return self.crossfile

	def concatenate_chunk(self):
		command = 'ffmpeg -y -i concat:%s|%s -c copy %s' % (self.chunk1, 
													self.crossfile, self.output)
		self.run(command)

	def run(self, command):
		r = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)
		out, err = r.communicate()

	def remove_old_file(self):
		files = os.listdir(self.out_directory)
		file_count = len(files)
		if file_count >= 100:
			client = new_mpd_client()
			playlist = [p['file'].replace('file://%s' % self.out_directory, '') 
									for p in client.playlistinfo()]
			not_in_playlist = tuple(file for file in files if file not in playlist)
			for n in not_in_playlist:
				path = '%s%s' % (self.out_directory, n)
				try:
					os.remove(path)
				except:
					pass

			
