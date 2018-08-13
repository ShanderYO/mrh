# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import logging
from os import makedirs
from os.path import isfile, isdir, join, dirname, basename
import time
import requests
import threading
import shutil
from concurrent.futures import Future, ThreadPoolExecutor, wait, as_completed, TimeoutError
from collections import deque
from .mpd_client import new_mpd_client, load_playlist, get_next_load_tracks
from mopidy import backend
import urllib2
from .utils import (concatenate_filename, check_crossfade_file, get_crossfade_file_path,
                        check_files_async, get_musicbox_id, get_entries)
from mopidy.m3u.playlists import M3UPlaylistsProvider
from .crossfade import Crossfade


logger = logging.getLogger(__name__)

class MuzlabPlaylistsProvider(M3UPlaylistsProvider):

    def __init__(self, backend, config):
        super(MuzlabPlaylistsProvider, self).__init__(backend, config)
        ext_config = config['muzlab']
        self._playlists_dir = ext_config['playlists_dir']
        self._base_dir = ext_config['base_dir'] or self._playlists_dir
        self._default_encoding = ext_config['default_encoding']
        self._playlist = ext_config['playlist']
        self._crossfade = ext_config['crossfade']
        self._playlist_uri = 'https://muz-lab.ru/api/v1/stream/playlist_musicbox/%s/' % get_musicbox_id()
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
            return logger.error('Playlist is downloaded is too short and not accepted !!!')
        return True

    def check_playlist_files(self, path, checked=[]):
        t0 = round(time.time())
        logger.info('Start check playlist %s' % path)
        infile = open(path, 'r')
        readlines = infile.readlines()
        entries = get_next_load_tracks(get_entries(readlines))
        accepted = check_files_async(entries, checked)
        exist_files = set(tuple(e[1] for e in entries if isfile(e[1])))
        not_exists_files = set(tuple(e[1] for e in entries if not isfile(e[1])))
        if self._crossfade:
            entries_count = len(entries)
            not_exists = tuple(entry for n, entry in enumerate(entries)
                if entry[1] not in exist_files or entries_count <= n + 1 or not check_crossfade_file(entry, entries[n+1]))
        else:
            not_exists = tuple(entry for entry in entries
                if entry[1] not in exist_files)
        t = round(time.time()) - t0
        logger.info('Accepted entries: %s' % len(accepted))
        logger.info('All playlist\'s entries: %s' % len(entries))
        logger.info('Not existing entries: %s' % len(not_exists))
        logger.info('Exist files: %s' % len(exist_files))
        logger.info('All files: %s' % str(len(exist_files) + len(not_exists_files)))
        logger.info('Not existing files: %s' % len(not_exists_files))
        logger.info('End check playlist %s %s sec' % (path, t))
        return (accepted, not_exists, entries)

    def sync_tracks(self, entries, is_crossfade=False):
        if not entries:
            return
        result = self.sync_tracks_concurrency(entries, is_crossfade=is_crossfade)
        while not result.done():
            try:
                result.result(.5)
            except TimeoutError:
                pass

    def create_playlist_file(self, entries, filename='main.m3u'):
        path = join(self._playlists_dir, filename)
        with open(path, 'wb') as f:
            for n, e in enumerate(entries):
                try:
                    next_ = entries[n+1]
                except IndexError:
                    break
                if self._crossfade:
                    path = get_crossfade_file_path(e[1], next_[1])
                else:
                    path = e[1]
                f.write(e[0])
                f.write('%s\n' % path)

    def sync_tracks_concurrency(self, entries, concurrency=4, is_crossfade=False):
        def download_tracks(entrie):
            url = entrie[1][1].replace('\n', '')
            n = entrie[0]
            load = True
            if not isfile(url):
                load = False
                if not isdir(dirname(url)):
                    makedirs(dirname(url))
                base_name = basename(url)
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
                prev = entries[n-1]
                add_crossfade(prev, entrie[1], n-1)

        def add_crossfade(entrie, next_, n):
            cut_start = False if n == 0 else True
            try:
                track_duration = int(entrie[0].decode('utf-8').split('duration=')[1].split(',')[0])/1000
            except (IndexError, ValueError, TypeError):
                track_duration = None
            crossfade = Crossfade(track=entrie[1], next_=next_[1], cut_start=cut_start, track_duration=track_duration)
            crossfade.add_crossfade()

        def submit():
            try:
                entrie = iterator.next()
            except StopIteration:
                return
            stats['delayed'] += 1
            future = executor.submit(download_tracks, entrie)
            future.obj = entrie
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

        iters = []
        not_exists_files = []
        for e in entries:
            if e and e[1] not in not_exists_files:
                iters.append(e)
                not_exists_files.append(e[1])
        iterator = enumerate(iters)
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
        logger.info('Download playlist !!!')
        logger.info(self._playlist_uri)
        try:
            r = requests.get(self._playlist_uri, stream=True, timeout=(5, 60))
        except requests.exceptions.ReadTimeout:
            return logger.error('Error Read timeout occured')
        except requests.exceptions.ConnectTimeout, requests.exceptions.Timeout:
            return logger.error('Error Connection timeout occured')
        except requests.exceptions.ConnectionError:
            return logger.error('Connection error')
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
        repeat = 1
        is_download = self.download_playlist(playlist=self._playlist.split(':')[0])
        accepted, not_exists, entries = self.check_playlist_files(self.last_playlist)
        client = new_mpd_client()
        if not client:
            return logger.warning('Can t mpd connect')
        if not entries:
            client.load('main')
        client.repeat(repeat)
        status = client.status()
        if is_download:
            logger.info('Download playlists done')
        if entries:
            if len(accepted) < 10:
                self.sync_tracks(entries[:10], is_crossfade=self._crossfade)
                checked = [i[1] for i in accepted]
                accepted, not_exists, entries = self.check_playlist_files(self.last_playlist, checked=checked)
            self.create_playlist_file(accepted)
            client = new_mpd_client()
            try:
                load_playlist(client)
            except Exception as es:
                return logger.error(es)
        try:
            if status['state'] != 'play' or status['time'] == '0:0':
                client.play()
        except Exception as es:
            logger.error(es)
        self.sync_tracks(not_exists)

