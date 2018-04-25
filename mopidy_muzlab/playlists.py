# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
import os
import requests
import threading
import shutil
from concurrent.futures import Future, ThreadPoolExecutor, wait, as_completed, TimeoutError
from collections import deque
from .mpd_client import new_mpd_client, load_playlist, get_next_load_tracks
from mopidy import backend
import urllib2
from .utils import concatenate_filename, get_duration, get_file_name
from mopidy.m3u.playlists import M3UPlaylistsProvider
from .crossfade import Crossfade

logger = logging.getLogger(__name__)

def check_line(line):
    if (line[0].decode('utf-8').startswith('#EXTINF') 
            and line[1].decode('utf-8').endswith('mp3\n')):
        return True

def get_crossfade_file_path(path, next_path, crossfade_directory='/tmp/crossfade'):
    return '%s/%s' % (crossfade_directory, concatenate_filename(path, next_path))

class MuzlabPlaylistsProvider(M3UPlaylistsProvider):

    def __init__(self, backend, config):
        super(MuzlabPlaylistsProvider, self).__init__(backend, config)
        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._base_dir = ext_config['base_dir'] or self._playlists_dir
        self._default_encoding = ext_config['default_encoding']
        self._playlist = ext_config['playlist']
        self._crossfade = ext_config['crossfade']
        self._link = ext_config['link']
        self._playlist_url = ext_config['playlist_url']
        self._default_extension = ext_config['default_extension']
        self.last_playlist = '/home/mopidy/mopidy/playlists/last_playlist.m3u'
        self.tmp_playlist = '/tmp/playlist.m3u'
        self.backend = backend

    def check_playlist(self, path):
        infile = open(path, 'r')
        playlist_type = infile.readline()
        playlist_number = infile.readline()
        readlines = infile.readlines()
        if not playlist_type.startswith('#EXTM3U'):
            return logger.error('Playlist have incorrect format')
        if not playlist_number.startswith('#PLAYLIST'):
            return logger.error('Playlist have incorrect format')
        if len(readlines) < 60:
            return logger.error('Playlist too showrt')
        return True

    def check_playlist_files(self, path):
        infile = open(path, 'r')
        playlist_type = infile.readline()
        playlist_number = infile.readline()
        readlines = infile.readlines()
        exists, not_exists, tracks = [], [], []
        for n, line in enumerate(readlines):
            if n % 2 != 0:
                continue
            try:
                file_path = readlines[n+1]
            except IndexError:
                break
            entry = (line, file_path)
            if not check_line((line, file_path)):
                continue
            tracks.append(entry)
            filename = get_file_name(entry)
            if not os.path.exists(filename) or os.stat(filename).st_size <= 1024:
                try:
                    os.remove(filename)
                except OSError:
                    pass
                not_exists.append(entry)
                continue
            else:
                exists.append(entry)
            if self._crossfade:
                try:
                    next_file_path = readlines[n+3]
                except IndexError:
                    break
                cross_file = get_crossfade_file_path(filename.decode('utf-8'), 
                            next_file_path.decode('utf-8').replace('\n', ''))
                if not os.path.exists(cross_file):
                    not_exists.append(entry)
                    continue
            
        # logger.info('exists: %s, not_exists: %s' % (len(exists), len(not_exists)))
        return (exists, not_exists, tracks)

    def sync_tracks(self, tracks, is_crossfade=False):
        result = self.sync_tracks_concurrency(tracks, is_crossfade=is_crossfade)
        while not result.done():
            try:
                result.result(.5)
            except TimeoutError:
                pass

    def create_playlist_file(self, tracks, filename='main.m3u'):
        path = os.path.join(self._playlists_dir, filename)
        playlist_type = '#EXTM3U'
        with open(path, 'wb') as f:
            f.write(playlist_type)
            for n, e in enumerate(tracks):
                try:
                    next_ = tracks[n+1]
                except IndexError:
                    break
                if self._crossfade:
                    path = get_crossfade_file_path(e[1], next_[1])
                else:
                    path = e[1]
                f.write(e[0])
                f.write('%s\n' % path)

    def sync_tracks_concurrency(self, lines, concurrency=4, is_crossfade=False):
        def download_tracks(obj):
            url = obj[1][1].replace('\n', '')
            n = obj[0]
            load = True
            if not os.path.exists(url):
                load = False
                if not os.path.exists(os.path.dirname(url)):
                    os.makedirs(os.path.dirname(url))
                base_name = os.path.basename(url)
                mp3file = urllib2.urlopen('http://f.muz-lab.ru/'+ base_name)
                try:
                    with open('/tmp/' + base_name, 'wb') as output:
                        output.write(mp3file.read())
                    shutil.move('/tmp/' + base_name,url)
                    logger.info(' File %s downloaded'%(url))
                    load = True
                except Exception as es:
                    logger.info(str(es))
            if is_crossfade and load and n > 0:
                prev = lines[n-1]
                add_crossfade(prev, obj[1], n-1)

        def add_crossfade(track, next_, n):
            cut_start = False if n == 0 else True
            try:
                track_duration = int(track[0].decode('utf-8').split('duration=')[1].split(',')[0])/1000
            except (IndexError, ValueError, TypeError):
                track_duration = get_duration(track[1])
            if not track_duration:
                logger.error('Failed get track duration %s' % track)
                return
            crossfade = Crossfade(track=track[1], next_=next_[1], cut_start=cut_start, track_duration=track_duration)
            crossfade.add_crossfade()

        def submit():
            try:
                obj = iterator.next()
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

        iterator = enumerate(lines)
        io_lock = threading.RLock()
        executor = ThreadPoolExecutor(concurrency)
        result = Future()
        result.stats = stats = {'done': 0, 'delayed': 0}
        result.add_done_callback(cleanup)

        with io_lock:
            for _ in range(concurrency):
                submit()
        return result

    def download_playlist(self, playlist):
        uri = '%s/%s' % (self._playlist_url, playlist)
        logger.info('Download playlist !!!')
        logger.info(uri)
        try:
            r = requests.get(uri, stream=True, timeout=(5, 60))
        except requests.exceptions.ReadTimeout:
            return logger.error('Error Read timeout occured')
        except requests.exceptions.ConnectTimeout, requests.exceptions.Timeout:
            return logger.error('Error Connection timeout occured')
        except Exception as es:
            return logger.error(es)

        if r.status_code == 200:
            with open(self.tmp_playlist, 'wb') as f:
                for chunk in r:
                    f.write(chunk)
            if(self.check_playlist(self.tmp_playlist)):
                shutil.move(self.tmp_playlist, self.last_playlist)
                return True
        else:
            return logger.error('Download failed')

    def refresh(self):
        current = 'main'
        repeat = 1
        is_download = self.download_playlist(playlist=self._playlist.split(':')[0])
        exists, not_exists, tracks = self.check_playlist_files(self.last_playlist)
        client = new_mpd_client()
        if not client:
            return logger.warning('Can t mpd connect')
        client.repeat(repeat)
        status = client.status()
        if is_download or status['playlistlength'] == '0':
            next_tracks = get_next_load_tracks(tracks)
            self.sync_tracks(next_tracks[:10], is_crossfade=self._crossfade)
            exists, not_exists, tracks = self.check_playlist_files(self.last_playlist)
            self.create_playlist_file(exists)
            try:
                load_playlist(client)
            except Exception as es:
                return logger.error(es)
        try:
            if status['state'] != 'play':
                client.play()
        except Exception as es:
            logger.error(es)
        self.sync_tracks(not_exists)



