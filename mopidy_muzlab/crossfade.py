import os
import subprocess
import time
import datetime as dt
import logging
from .utils import concatenate_filename
from .mpd_client import new_mpd_client

logger = logging.getLogger(__name__)

class Crossfade(object):

	def __init__(self, track, next_, crossfade=5, out_directory='/tmp/crossfade/', out_file=None,
						cut_first=False, track_duration=None, curve='qsin'):
		self.track = track.replace('\n', '')
		self.next_ = next_.replace('\n', '')
		self.cut_first = cut_first
		self.crossfade = crossfade
		self.track_duration = track_duration
		self.out_file = out_file if out_file else concatenate_filename(self.track, self.next_)
		self.curve = curve
		if not os.path.exists(os.path.dirname(out_directory)):
			os.makedirs(os.path.dirname(out_directory))
		self.output = '%s%s' % (out_directory, self.out_file)

	def add_crossfade(self):
		if (os.path.exists(self.output) 
			or not os.path.exists(self.track)  
			or not os.path.exists(self.next_)
			or not self.track_duration):
			return
		chunk1, chunk2 = self.split_track()
		crossfile = self.add_crossfade_between_files()
		self.concatenate_chunk()
		if self.cut_first:
			self.cut()
		logger.info('Crossfade:%s' % self.output)
		for f in [chunk1, chunk2, crossfile]:
			try:
				os.remove(f)
			except:
				pass
		self.remove_old_file()
		return self.output

	def split_track(self):
		splitting = self.track_duration - self.crossfade
		chunk1 = '/tmp/%s' % self.track.split('/')[-1].replace('.mp3','.chunk1.mp3')
		chunk2 = '/tmp/%s' % self.track.split('/')[-1].replace('.mp3','.chunk2.mp3')
		command1 = 'ffmpeg -y -ss 0 -t %s -i %s -c copy %s' % (splitting, self.track, chunk1)
		command2 = 'ffmpeg -y -ss %s -i %s -c copy %s' % (splitting, self.track, chunk2)
		self.run(command1)
		self.run(command2)
		self.chunk1, self.chunk2 = chunk1, chunk2
		return [self.chunk1, self.chunk2]

	def cut(self):
		command = 'ffmpeg -y -ss %s -i %s -c copy %s' % (self.crossfade, self.output, '%s.cut' % self.output)
		self.run(command)
		
	def add_crossfade_between_files(self):
		crossfile = '/tmp/%s' % self.chunk2.split('/')[-1].replace('.chunk2.mp3', '.cross.mp3')
		filter_complex = '[1]atrim=0:3.01[b];[0][b]acrossfade=d=%s:c1=%s:c2=%s' % (self.crossfade, 
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
									for p in c.playlistinfo()]
			[os.remove('%s%s' % (self.out_directory, file)) 
										for file in files if file in playlist]
