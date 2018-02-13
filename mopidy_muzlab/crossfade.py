import os
import subprocess
import time
import datetime as dt

class Crossfade(object):

	def __init__(self, track, next_, crossfade=3, out_directory='/tmp', out_file=None,
						cut_first=False, track_duration=None, next_duration=None,
												curve='qsin'):
		self.track = track
		self.next_ = next_
		self.cut_first = cut_first
		self.crossfade = crossfade
		self.track_duration = track_duration if track_duration else self.get_duration(self.track)
		self.next_duration = next_duration if next_duration else self.get_duration(self.next_)
		self.out_file = out_file if out_file else self.track.split('/')[-1]
		self.curve = curve
		self.output = '%s/%s' % (out_directory, self.out_file)

	def add_crossfade(self):
		chunk1, chunk2 = self.split_track()
		crossfile = self.add_crossfade_between_files()
		out = self.concatenate_chunk()
		if self.cut_first:
			self.cut()
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
		command = 'ffmpeg -y -ss %s -i %s -c copy %s' % (self.crossfade, self.track, track)
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

	def file_exists_timeout():
		'''
			Will read decorator for timeout if chunk files not exists yet
		'''
		pass

	def get_duration(self, track):
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
				duration = dt.timedelta(hours=data[0], minutes=data[1], 
											seconds=data[2], microseconds=data[3]).total_seconds()
			except ValueError:
				return
			return duration

	def run(self, command):
		r = subprocess.Popen(command.split(), stdout=subprocess.PIPE, stderr = subprocess.PIPE)
		out, err = r.communicate()
