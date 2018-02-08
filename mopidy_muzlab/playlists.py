# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import contextlib
import io
import locale
import logging
import operator
import os
import requests
import shutil
from .mpd_client import new_mpd_client
from datetime import datetime as dt
from mopidy import backend
import urllib2
from mopidy.m3u.playlists import log_environment_error, replace, M3UPlaylistsProvider

from . import translator

logger = logging.getLogger(__name__)

def get_correct_playlist(_playlist):
        current_hour = int(dt.now().strftime('%H'))
        periud = _playlist.split(',')[0].split(':')[1].split('-')
        periud = range(int(periud[0]), int(periud[1]))
        if current_hour in periud:
            logger.info('main playlist')
            return 'main'
        else:
            logger.info('second playlist')
            return 'second'

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
        entry = []
        for i,line in enumerate(lines):
            if i%2 == 1:
                continue
            try:
                n = [line, lines[i+1]]
                entry.append(n)
            except IndexError:
                pass
        self.sync_tracks(entry)
        entry = [e for e in entry if len(e) == 2 and
                                     e[0].decode('utf-8').startswith('#EXTINF') and
                                     e[1].decode('utf-8').endswith('mp3\n') and
                                     os.path.exists(self.get_file_name(e)) and
                                     os.stat(self.get_file_name(e)).st_size > 1024
                                     ]
        with open(path, 'wb') as f:
            f.write(playlist_type)
            f.write(playlist_number)
            for e in entry:
                f.write(e[0])
                f.write(e[1])
        return True

    def sync_tracks(self, entry):
        from concurrent.futures import ThreadPoolExecutor, wait, as_completed

        def download_tracks(url):
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
                logger.info(str(es))

        pool = ThreadPoolExecutor(2)
        tracks_not_exists = [self.get_file_name(e) for e in entry if len(e) == 2 and not os.path.exists(self.get_file_name(e))]
        futures = [pool.submit(download_tracks, url) for url in tracks_not_exists[:5]]
        return [r.result() for r in as_completed(futures)]

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
        except requests.exceptions.ConnectionError as error:
            return logger.error(error)

        if r.status_code == 200:
            with open(tempfile, 'wb') as f:
                for chunk in r:
                    f.write(chunk)

            if(self.check_playlist(tempfile)):
                shutil.move(tempfile, path)
            else:
                logger.error('Download playlist is not correcty')
        else:
            logger.error('Download failed')

    def make_playlist_for_link(self):
        link = self._link
        path_link = os.path.join(self._playlists_dir, 'link.m3u')
        path_main = os.path.join(self._playlists_dir, 'main.m3u')
        lines = ['#EXTM3U\n','#EXTINF:-1,Link\n',link+'\n']
        logger.info(lines) 
        with open(path_main, 'r') as fm:
            for i,line in enumerate(fm.readlines()[1:]):
                logger.info(line)
                lines.append(line)
                if i%2 != 0:
                    continue
                lines.append('#EXTINF:-1,Link\n')
                lines.append(link+'\n')
        # logger.info(lines) 
        with open(path_link, 'wb') as fl:
            for line in lines:
                fl.write(line)
        return True

    def clear(self, client):
        while True:
            status = client.status()
            if status['playlistlength'] in ['0', '1']:
                break
            if hasattr(status, 'song') and status['song'] != '0':
                client.delete(0)
            else:
                client.delete(1)

    def refresh(self):
        try:
            playlist = self._playlist.split(',')[0].split(':')[0]
            self.download_playlist(playlist=playlist, filename='main.m3u')
            playlist_second = self._playlist.split(',')[1].split(':')[0]
            self.download_playlist(playlist=playlist_second, filename='second.m3u')
        except:
            pass
        if self._cast_type == 'playlist':
            current = get_correct_playlist(self._playlist)
            repeat = 0
        elif self._cast_type == 'link':
            self.make_playlist_for_link()
            current = 'link'
            repeat = 1
        try:
            client = new_mpd_client()    
            self.clear(client)
            client.repeat(repeat)
            client.load(current)
            status = client.status()
            try:
                song = int(status['song'])
            except:
                song = 0
            if current == 'link':
                client.load('main')
            if status['state'] != 'play':
                client.play()
            if status['state'] == 'play' and current == 'link' and song not in [0,1]:
                client.play(0)
        except Exception as es:
            logger.error(es) 
