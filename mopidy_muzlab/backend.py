# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
import os
import time
import subprocess
import pykka
from threading import Lock
from mopidy import backend
from mopidy.audio import Audio
from .playlists import MuzlabPlaylistsProvider
from .repeating_timer import RepeatingTimer
from .mpd_client import new_mpd_client, load_playlist

logger = logging.getLogger(__name__)


class MuzlabAudio(Audio):
    def __init__(self, config):
        super(MuzlabAudio, self).__init__(config, None)
        ext_config = config['muzlab']


class MuzlabBackend(pykka.ThreadingActor, backend.Backend):
    uri_schemes = ['muzlab']

    def __init__(self, config, audio):
        super(MuzlabBackend, self).__init__()

        ext_config = config['muzlab']
        self._video_control = ext_config['video_control']
        self._refresh_playlists_rate = 300
        self._refresh_playlists_timer = None
        self._playlist_lock = Lock()
        self._observer_lock = Lock()
        self._omxplayer_observer_lock = Lock()
        self.audio = MuzlabAudio(config)
        self.playback = backend.PlaybackProvider(audio, self)
        self.playlists = MuzlabPlaylistsProvider(self, config)
        self._observer_rate = 10
        self._observer_init = False
        self._omxplayer_observer_rate = 0.1
        self._omxplayer_observer_timer = None
        self._pause = False

    def on_start(self):
        logger.info('Start backend!!!')
        if self._video_control:
            self._omxplayer_observer_timer = RepeatingTimer(
                self._omxplayer_observer,
                self._omxplayer_observer_rate)
            self._omxplayer_observer_timer.start()
        self._refresh_playlists_timer = RepeatingTimer(
            self._refresh_playlists,
            self._refresh_playlists_rate)
        self._refresh_playlists_timer.start()
        self._observer_timer = RepeatingTimer(
            self._observer,
            self._observer_rate)
        self._observer_timer.start()

    def on_stop(self):
        if self._video_control:
            try:
                self._omxplayer_observer_timer.cancel()
            except:
                pass
            self._omxplayer_observer_timer = None
        try:
            self._refresh_playlists_timer.cancel()
        except:
            pass
        self._refresh_playlists_timer = None
        try:
            self._observer_timer.cancel()
        except:
            pass
        self._observer_timer = None

    def _observer(self):
        with self._observer_lock:
            pos = self.playback.get_time_position()
            if pos != 0:
                self._observer_init = True
            if self._observer_init and not self._pause:
                time.sleep(0.2)
                pos_ = self.playback.get_time_position()
                if pos != pos_:
                    return
                try:
                    client = new_mpd_client()
                    client.play()
                    time.sleep(0.2)
                    pos__ = self.playback.get_time_position()
                    if pos_ != pos__:
                        return
                    load_playlist(client)
                    client.play()
                    time.sleep(0.2)
                    if pos__ != self.playback.get_time_position():
                        self._refresh_playlists()
                except Exception as es:
                    logger.info(str(es))

    def resume(self):
        try:
            self._pause = not self.playback.resume()
            # logger.info('AUDIO YES')
        except AttributeError:
            pass

    def pause(self):
        try:
            self._pause = self.playback.pause()
            # logger.info('AUDIO NO')
        except AttributeError:
            pass

    def _omxplayer_observer(self):
        with self._omxplayer_observer_lock:
            # logger.info('Start omxplayer_observer')
            ps = subprocess.Popen(['ps', '-aux'],stdout=subprocess.PIPE)
            proc = [p for p in ps.stdout.readlines() if '/usr/bin/omxplayer.bin' in p]
            mp4 = ''
            if not proc and self._pause == True:
                self.resume()
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
            if not os.path.exists(mp4) and self._pause == True:
                self.resume()
            info = subprocess.Popen(['ffprobe', '-i', mp4], stdout=subprocess.PIPE,
                                                         stdin=subprocess.PIPE, 
                                                         stderr=subprocess.PIPE).stderr.read()
            if 'Audio' in info and self._pause == False: 
                self.pause()
            elif 'Audio' not in info and self._pause == True:
                self.resume()

    def _refresh_playlists(self):
        with self._playlist_lock:
            t0 = round(time.time())
            logger.info('Start refreshing playlists')
            self.playlists.refresh()
            t = round(time.time()) - t0
            logger.info('Finished refreshing playlists in %ds', t)
