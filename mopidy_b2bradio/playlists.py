from __future__ import absolute_import, unicode_literals

import contextlib
import io
import locale
import logging
import operator
import os
import urllib

from mopidy import backend

from . import translator

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
        self._default_extension = ext_config['default_extension']

    def check_playlist(self, infile):
        try:
            assert(type(infile) == '_io.TextIOWrapper')
        except AssertionError:
            infile = open(infile,'r')
        line = infile.readline()
        if not line.startswith('#EXTM3U'):
            return
        return True

    def _abspath(self, path):
        return os.path.join(self._playlists_dir, path)

    def refresh(self):
        playlist = '1.m3u'
        directory = '/home/test/mopidy/playlists/'
    	url = 'http://lukoil2.muzis.ru/api/v1/stream/playlist_box/%s' % (playlist)
        tempfile = '/tmp/new_playlist.m3u'

    	logger.info('Download playlist !!!')
        pfile = urllib.URLopener()
    	try:
    	   pfile.retrieve(url, '/tmp/new_playlist.m3u')
    	except:
            logger.error('Error loading playlist')
            return
        if(self.check_playlist('/tmp/new_playlist.m3u')):
            os.rename(tempfile, os.path.join(directory,playlist))
        else:
            logger.error('Download playlist is not correcty')
