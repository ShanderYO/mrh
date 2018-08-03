#!/usr/bin/env python

import os
import time
import subprocess
from mopidy_muzlab.playlists import new_mpd_client


def check_omxplay():
    ps = subprocess.Popen(['ps', '-aux'],stdout=subprocess.PIPE)
    proc = [p for p in ps.stdout.readlines() if '/usr/bin/omxplayer.bin' in p]
    mp4 = ''
    if not proc:
        return False
    if len(proc) > 1:
        try:
            mp4 = '/home/files/%s' % proc[0].split('/home/files/')[1].split()[0]
        except (KeyError, IndexError):
            pass
    else:
        try:
            mp4 = '/home/files/%s' % proc[0].split('/home/files/')[1].split('\n')[0]
        except (KeyError, IndexError):
            pass
    mp4 = mp4.split()[0] if mp4 else ''
    if not os.path.isfile(mp4):
        return False
    info = subprocess.Popen(['ffprobe', '-i', mp4], stdout=subprocess.PIPE,
                                                 stdin=subprocess.PIPE, 
                                                 stderr=subprocess.PIPE).stderr.read()
    if 'Audio' in info: 
        return True
    else:
        return False

def main():
    if check_omxplay():
        return True
    try:
        t1 = new_mpd_client().status()['time']
    except:
        return False
    time.sleep(1)
    try:
        t2 = new_mpd_client().status()['time']
    except:
        return False
    if t1 == t2:
        return False
    return True

if __name__ == "__main__":
    import sys
    # calculate stuff
    sys.stdout.write('%s\n'%(1 if main() else 0))
    sys.stdout.flush()
    sys.exit(0)