import os
import subprocess
import time


def add_crossfade(track, next_, is_first=False):
	splitting = 411
	chunk1, chunk2 = split_track(track, splitting)
	time.sleep(1)
	crossfile = add_crossfade_between_chunks(chunk2, next_)
	time.sleep(1)
	out = concatenate_chunk(chunk1, crossfile)
	time.sleep(1)
	if is_first:
		out = cut(out)
	return out

def split_track(track, splitting):
	chunk1 = '/tmp/%s' % track.split('/')[-1].replace('.mp3','.chunk1.mp3')
	chunk2 = '/tmp/%s' % track.split('/')[-1].replace('.mp3','.chunk2.mp3')
	command1 = 'ffmpeg -y -ss 0 -t %s -i %s -c copy %s' % (splitting, track, chunk1)
	command2 = 'ffmpeg -y -ss %s -i %s -c copy %s' % (splitting, track, chunk2)
	run(command1)
	run(command2)
	return [chunk1, chunk2]

def cut(track, cut):
	command = 'ffmpeg -y -ss %s -i %s -c copy %s' % (splitting, track, track)
	run(command)
	
def add_crossfade_between_chunks(chunk, next_, duration=3.0, curve='qsin'):
	crossfile = '/tmp/%s' % chunk.split('/')[-1].replace('.chunk2.mp3', '.cross.mp3')
	filter_complex = '[1]atrim=0:3.01[b];[0][b]acrossfade=d=%s:c1=%s:c2=%s' % (duration, 
														curve, curve)
	command = 'ffmpeg -y -i %s -i %s -filter_complex %s %s' % (chunk, 
								next_, filter_complex, crossfile)
	run(command)
	return crossfile

def concatenate_chunk(chunk1, crossfile):
	out = chunk1.replace('.chunk1', '')
	command = 'ffmpeg -y -i concat:%s|%s -c copy %s' % (chunk1, crossfile, out)
	run(command)

def file_exists_timeout():
	'''
		Will read decorator for timeout if chunk files not exists yet
	'''
	pass

def run(command):
	subprocess.Popen(command.split(), stdout=subprocess.PIPE)

