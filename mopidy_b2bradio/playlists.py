# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import io
import locale
import logging
import os
import requests
import shutil
from .mpd_client import new_mpd_client

from mopidy import backend

logger = logging.getLogger(__name__)


def log_environment_error(message, error):
    if isinstance(error.strerror, bytes):
        strerror = error.strerror.decode(locale.getpreferredencoding())
    else:
        strerror = error.strerror
    logger.error('%s: %s', message, strerror)


class B2bradioPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, backend, config):
        super(B2bradioPlaylistsProvider, self).__init__(backend)

        ext_config = config['b2bradio']
        # if ext_config['playlists_dir'] is None:
        #     self._playlists_dir = Extension.get_data_dir(config)
        # else:
        self._playlists_dir = ext_config['playlists_dir']
        self._base_dir = ext_config['base_dir'] or self._playlists_dir
        self._default_encoding = ext_config['default_encoding']
        self._playlist = ext_config['playlist']
        self._playlist_url = ext_config['playlist_url']
        self._default_extension = ext_config['default_extension']

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
        entry = [e for e in entry if len(e) == 2 and 
                                     e[0].decode('utf-8').startswith('#EXTINF') and 
                                     e[1].decode('utf-8').endswith('mp3\n') and 
                                     os.path.exists(e[1].replace('\n', ''))]
        with open(path, 'wb') as f:
            f.write(playlist_type)
            f.write(playlist_number)
            for e in entry:
                f.write(e[0])
                f.write(e[1])
        return True

    def _abspath(self, path):
        return os.path.join(self._playlists_dir, path)

    def refresh(self):
        uri = '%s/%s' % (self._playlist_url, self._playlist)
        tempfile = '/tmp/new_playlist.m3u'
        path = os.path.join(self._playlists_dir,'main.m3u')

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
                try:
                    client = new_mpd_client()
                    client.clear()
                    client.load('main')
                    client.play()
                except:
                    pass
            else:
                logger.error('Download playlist is not correcty')
        else:
            logger.error('Download failed')