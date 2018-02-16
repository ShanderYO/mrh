# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import contextlib
import io
import locale
import logging
import operator
import os
import time
import requests
import threading
import shutil
from concurrent.futures import Future, ThreadPoolExecutor, wait, as_completed, TimeoutError
from collections import deque
from .mpd_client import new_mpd_client, clear_playlist
from datetime import datetime as dt
from mopidy import backend
import urllib2
from .utils import concatenate_filename
from mopidy.m3u.playlists import log_environment_error, replace, M3UPlaylistsProvider
from .crossfade import Crossfade
from . import translator

logger = logging.getLogger(__name__)

def get_correct_playlist(_playlist):
        playlists = _playlist.split(',')
        if len(playlists) == 1:
            return 'main'
        current_hour = int(dt.now().strftime('%H'))
        for n, playlist in enumerate(_playlist.split(',')):
            day = deque(i+1 for i in xrange(24))
            start, end = playlist.split(':')[1].split('-')
            day.rotate(24-int(start)+1)
            day = list(day)
            periud = day[:day.index(int(end))]
            if current_hour in periud:
                plname = 'main%s'%str(n)
                logger.info('Current playlist %s'%plname)
                return plname

class MuzlabPlaylistsProvider(M3UPlaylistsProvider):

    def __init__(self, backend, config):
        super(MuzlabPlaylistsProvider, self).__init__(backend, config)

        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._base_dir = ext_config['base_dir'] or self._playlists_dir
        self._default_encoding = ext_config['default_encoding']
        self._playlist = ext_config['playlist']
        self._cast_type = ext_config['cast_type']
        self._link = ext_config['link']
        self._playlist_url = ext_config['playlist_url']
        self._default_extension = ext_config['default_extension']
        self.backend = backend

    def get_file_name(self,e):
        return e[1].replace('\n', '')

    def check_playlist(self, path):
        try:
            assert(type(path) == '_io.TextIOWrapper')
        except AssertionError:
            infile = open(path,'r')
        playlist_type = infile.readline()
        if not playlist_type.startswith('#EXTM3U'):
            return
        playlist_number = infile.readline()
        if not playlist_number.startswith('#PLAYLIST'):
            return
        lines = infile.readlines()
        entry, notexists = [], []
        for i,line in enumerate(lines):
            if i%2 == 1:
                continue
            try:
                e = [line, lines[i+1]]
                if e[0].decode('utf-8').startswith('#EXTINF') and e[1].decode('utf-8').endswith('mp3\n'):
                    filename = self.get_file_name(e)
                    is_exist = os.path.exists(filename)
                    if is_exist and os.stat(filename).st_size > 1024:
                        entry.append(e)
                    elif is_exist and not os.stat(filename).st_size > 1024:
                        os.remove(filename)
                        notexists.append(e)
                    else:
                        notexists.append(e)
            except IndexError:
                pass
        exists_track = len(entry)
        min_track_count = 15
        if exists_track < min_track_count:
            result = self.sync_tracks(iter(notexists[:min_track_count]))
            logger.info('%s exists track' % exists_track)
            while not result.done():
                try:
                    result.result(.5)
                except TimeoutError:
                    pass
            entry.extend(notexists[:min_track_count])
        for n, e in enumerate(entry[:min_track_count]):
            cut_first = False if n == 0 else True
            try:
                next_ = entry[n+1]
            except:
                break
            # logger.info('%s %s %s' % (str(n), e, next_))
            crossfade = Crossfade(track=e[1], next_=next_[1], cut_first=cut_first)
            crossfade.add_crossfade()
        with open(path, 'wb') as f:
            f.write(playlist_type)
            f.write(playlist_number)
            for n, e in enumerate(entry):
                try:
                    path = '/tmp/crossfade/%s\n' % concatenate_filename(e[1], entry[n+1][1])
                except IndexError:
                    continue
                logger.info('path %s'%path)
                f.write(e[0])
                f.write(path)
        self.sync_tracks(iter(notexists[min_track_count:]))
        return True

    def sync_tracks(self, notexists, concurrency=4):

        def download_tracks(url):
            url = self.get_file_name(url)
            if os.path.exists(url):
                return
            if not os.path.exists(os.path.dirname(url)):
                os.makedirs(os.path.dirname(url))
            try:
                base_name = os.path.basename(url)
                mp3file = urllib2.urlopen('http://f.muz-lab.ru/'+ base_name)
                with open('/tmp/' + base_name, 'wb') as output:
                    output.write(mp3file.read())
                shutil.move('/tmp/' + base_name,url)
                logger.info(' File %s downloaded'%(url))
            except Exception as es:
                # logger.info(str(es))
                pass

        def submit():
            try:
                obj = notexists.next()
            except StopIteration:
                return
            stats['delayed'] += 1
            future = executor.submit(download_tracks, obj)
            future.obj = obj
            future.add_done_callback(download_done)

        def download_done(future):
            with io_lock:
                submit()
                stats['delayed'] -= 1
                stats['done'] += 1
            if future.exception():
                logger.error(future.exception())
            if stats['delayed'] == 0:
                result.set_result(stats)

        def cleanup(_):
            with io_lock:
                executor.shutdown(wait=False)

        io_lock = threading.RLock()
        executor = ThreadPoolExecutor(concurrency)
        result = Future()
        result.stats = stats = {'done': 0, 'delayed': 0}
        result.add_done_callback(cleanup)

        with io_lock:
            for _ in range(concurrency):
                submit()
        return result

    def download_playlist(self, playlist, filename):
        uri = '%s/%s' % (self._playlist_url, playlist)
        tempfile = '/tmp/new_playlist.m3u'
        path = os.path.join(self._playlists_dir, filename)

        logger.info('Download playlist !!!')
        logger.info(uri)
        try:
            r = requests.get(uri, stream=True, timeout=(5, 60))
        except requests.exceptions.ReadTimeout:
            return logger.error('Error Read timeout occured')
        except requests.exceptions.ConnectTimeout:
            return logger.error('Error Connection timeout occured')

        if r.status_code == 200:
            with open(tempfile, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

            if(self.check_playlist(tempfile)):
                shutil.move(tempfile, path)
            else:
                logger.warning('Download playlist is not correct')
        else:
            logger.error('Download failed')

    def make_playlist_for_link(self):
        link = self._link
        path_link = os.path.join(self._playlists_dir, 'link.m3u')
        path_main = os.path.join(self._playlists_dir, 'main.m3u')
        lines = ['#EXTM3U\n','#EXTINF:-1,Link\n',link+'\n']
        logger.info(lines) 
        with open(path_main, 'r') as fm:
            for i,line in enumerate(fm.readlines()[2:]):
                logger.info(line)
                lines.append(line)
                if i%2 != 0:
                    continue
                if i%10==0:
                    lines.append('#EXTINF:-1,Link\n')
                    lines.append(link+'\n')
        # logger.info(lines) 
        with open(path_link, 'wb') as fl:
            for line in lines:
                fl.write(line)
        return True

    def refresh(self):
        for n, playlist in enumerate(self._playlist.split(',')):
            try:
                playlist = playlist.split(':')[0]
            except IndexError:
                logger.warning('Playlist %s is not valid' % playlist)
            self.download_playlist(playlist=playlist, filename='main%s.m3u'%str(n))

        if self._cast_type == 'playlist':
            current = get_correct_playlist(self._playlist)
            repeat = 0
        elif self._cast_type == 'link':
            self.make_playlist_for_link()
            current = 'link'
            repeat = 1
        try:
            client = new_mpd_client()    
            clear_playlist(client)
            client.consume(1)
            client.repeat(repeat)
            client.load(current)
            status = client.status()
            try:
                song = int(status['song'])
            except:
                song = 0
            if status['state'] != 'play':
                client.play()
            if status['state'] == 'play' and current == 'link' and song not in [0,1]:
                client.play(0)
        except Exception as es:
            logger.error(es) 
