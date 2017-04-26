from __future__ import absolute_import, unicode_literals

import contextlib
import io
import locale
import logging
import operator
import os
import tempfile

from mopidy import backend

from . import Extension, translator

logger = logging.getLogger(__name__)


def log_environment_error(message, error):
    if isinstance(error.strerror, bytes):
        strerror = error.strerror.decode(locale.getpreferredencoding())
    else:
        strerror = error.strerror
    logger.error('%s: %s', message, strerror)


@contextlib.contextmanager
def replace(path, mode='w+b', encoding=None, errors=None):
    try:
        (fd, tempname) = tempfile.mkstemp(dir=os.path.dirname(path))
    except TypeError:
        # Python 3 requires dir to be of type str until v3.5
        import sys
        path = path.decode(sys.getfilesystemencoding())
        (fd, tempname) = tempfile.mkstemp(dir=os.path.dirname(path))
    try:
        fp = io.open(fd, mode, encoding=encoding, errors=errors)
    except:
        os.remove(tempname)
        os.close(fd)
        raise
    try:
        yield fp
        fp.flush()
        os.fsync(fd)
        os.rename(tempname, path)
    except:
        os.remove(tempname)
        raise
    finally:
        fp.close()


class B2bradioPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, backend, config):
        super(B2bradioPlaylistsProvider, self).__init__(backend)

        ext_config = config[Extension.ext_name]
        if ext_config['playlists_dir'] is None:
            self._playlists_dir = Extension.get_data_dir(config)
        else:
            self._playlists_dir = ext_config['playlists_dir']
        self._base_dir = ext_config['base_dir'] or self._playlists_dir
        self._default_encoding = ext_config['default_encoding']
        self._default_extension = ext_config['default_extension']

    def as_list(self):
        result = []
        for entry in os.listdir(self._playlists_dir):
            if not entry.endswith((b'.m3u', b'.m3u8')):
                continue
            elif not os.path.isfile(self._abspath(entry)):
                continue
            else:
                result.append(translator.path_to_ref(entry))
        result.sort(key=operator.attrgetter('name'))
        return result

    def create(self, name):
        path = translator.path_from_name(name.strip(), self._default_extension)
        try:
            with self._open(path, 'w'):
                pass
            mtime = os.path.getmtime(self._abspath(path))
        except EnvironmentError as e:
            log_environment_error('Error creating playlist %s' % name, e)
        else:
            return translator.playlist(path, [], mtime)

    def delete(self, uri):
        path = translator.uri_to_path(uri)
        try:
            os.remove(self._abspath(path))
        except EnvironmentError as e:
            log_environment_error('Error deleting playlist %s' % uri, e)

    def get_items(self, uri):
        path = translator.uri_to_path(uri)
        try:
            with self._open(path, 'r') as fp:
                items = translator.load_items(fp, self._base_dir)
        except EnvironmentError as e:
            log_environment_error('Error reading playlist %s' % uri, e)
        else:
            return items

    def lookup(self, uri):
        path = translator.uri_to_path(uri)
        try:
            with self._open(path, 'r') as fp:
                items = translator.load_items(fp, self._base_dir)
            mtime = os.path.getmtime(self._abspath(path))
        except EnvironmentError as e:
            log_environment_error('Error reading playlist %s' % uri, e)
        else:
            return translator.playlist(path, items, mtime)

    def refresh(self):
        pass  # nothing to do

    def save(self, playlist):
        path = translator.uri_to_path(playlist.uri)
        name = translator.name_from_path(path)
        try:
            with self._open(path, 'w') as fp:
                translator.dump_items(playlist.tracks, fp)
            if playlist.name and playlist.name != name:
                opath, ext = os.path.splitext(path)
                path = translator.path_from_name(playlist.name.strip()) + ext
                os.rename(self._abspath(opath + ext), self._abspath(path))
            mtime = os.path.getmtime(self._abspath(path))
        except EnvironmentError as e:
            log_environment_error('Error saving playlist %s' % playlist.uri, e)
        else:
            return translator.playlist(path, playlist.tracks, mtime)

    def _abspath(self, path):
        return os.path.join(self._playlists_dir, path)

    def _open(self, path, mode='r'):
        if path.endswith(b'.m3u8'):
            encoding = 'utf-8'
        else:
            encoding = self._default_encoding
        if not os.path.isabs(path):
            path = os.path.join(self._playlists_dir, path)
        if 'w' in mode:
            return replace(path, mode, encoding=encoding, errors='replace')
        else:
            return io.open(path, mode, encoding=encoding, errors='replace')



from mopidy.models import Playlist, Ref


class GMusicPlaylistsProvider(backend.PlaylistsProvider):

    def __init__(self, *args, **kwargs):
        super(GMusicPlaylistsProvider, self).__init__(*args, **kwargs)
        self._radio_stations_as_playlists = (
            self.backend.config['gmusic']['radio_stations_as_playlists'])
        self._radio_stations_count = (
            self.backend.config['gmusic']['radio_stations_count'])
        self._radio_tracks_count = (
            self.backend.config['gmusic']['radio_tracks_count'])
        self._playlists = {}

    def as_list(self):
        refs = [
            Ref.playlist(uri=pl.uri, name=pl.name)
            for pl in self._playlists.values()]
        return sorted(refs, key=operator.attrgetter('name'))

    def get_items(self, uri):
        playlist = self._playlists.get(uri)
        if playlist is None:
            return None
        return [Ref.track(uri=t.uri, name=t.name) for t in playlist.tracks]

    def lookup(self, uri):
        return self._playlists.get(uri)

    def refresh(self):
        playlists = {}

        # We need to grab all the songs for later. All access metadata
        # will be included with the playlist entry, but uploaded music
        # will not.
        library_tracks = {}
        for track in self.backend.session.get_all_songs():
            mopidy_track = self.backend.library._to_mopidy_track(track)
            library_tracks[track['id']] = mopidy_track

        # add thumbs up playlist
        tracks = []
        for track in self.backend.session.get_promoted_songs():
            tracks.append(self.backend.library._to_mopidy_track(track))

        if len(tracks) > 0:
            uri = 'gmusic:playlist:promoted'
            playlists[uri] = Playlist(uri=uri, name='Promoted', tracks=tracks)

        # load user playlists
        for playlist in self.backend.session.get_all_user_playlist_contents():
            tracks = []
            for entry in playlist['tracks']:
                if entry['deleted']:
                    continue

                if entry['source'] == u'1':
                    tracks.append(library_tracks[entry['trackId']])
                else:
                    entry['track']['id'] = entry['trackId']
                    tracks.append(self.backend.library._to_mopidy_track(
                        entry['track']))

            uri = 'gmusic:playlist:' + playlist['id']
            playlists[uri] = Playlist(uri=uri,
                                      name=playlist['name'],
                                      tracks=tracks)

        # load shared playlists
        for playlist in self.backend.session.get_all_playlists():
            if playlist.get('type') == 'SHARED':
                tracks = []
                tracklist = self.backend.session.get_shared_playlist_contents(
                    playlist['shareToken'])
                for entry in tracklist:
                    if entry['source'] == u'1':
                        tracks.append(library_tracks[entry['trackId']])
                    else:
                        entry['track']['id'] = entry['trackId']
                        tracks.append(self.backend.library._to_mopidy_track(
                            entry['track']))

                uri = 'gmusic:playlist:' + playlist['id']
                playlists[uri] = Playlist(uri=uri,
                                          name=playlist['name'],
                                          tracks=tracks)

        l = len(playlists)
        logger.info('Loaded %d playlists from Google Music', len(playlists))

        # load radios as playlists
        if self._radio_stations_as_playlists:
            logger.info('Starting to loading radio stations')
            stations = self.backend.session.get_radio_stations(
                self._radio_stations_count)
            for station in stations:
                tracks = []
                tracklist = self.backend.session.get_station_tracks(
                    station['id'], self._radio_tracks_count)
                for track in tracklist:
                    tracks.append(
                        self.backend.library._to_mopidy_track(track))
                uri = 'gmusic:playlist:' + station['id']
                playlists[uri] = Playlist(uri=uri,
                                          name=station['name'],
                                          tracks=tracks)
            logger.info('Loaded %d radios from Google Music',
                        len(playlists) - l)

        self._playlists = playlists
        backend.BackendListener.send('playlists_loaded')

    def create(self, name):
        raise NotImplementedError

    def delete(self, uri):
        raise NotImplementedError

    def save(self, playlist):
        raise NotImplementedError
