# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from os.path import join, dirname
import logging
from mopidy import config, ext
from .utils import get_musicbox_id, send_states

__version__ = '0.7.11'

logger = logging.getLogger(__name__)

class MuzlabExtension(ext.Extension):

    dist_name = 'Mopidy-Muzlab'
    ext_name = 'muzlab'
    _state_uri = 'https://muz-lab.ru/api/v1/stream/musicbox/%s/send_states/' % get_musicbox_id()
    version = __version__

    def get_default_config(self):
        conf_file = join(dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(MuzlabExtension, self).get_config_schema()
        schema['base_dir'] = config.Path(optional=True)
        schema['default_encoding'] = config.String()
        schema['default_extension'] = config.String(choices=['.m3u', '.m3u8'])
        schema['playlists_dir'] = config.Path(optional=True)
        schema['start_tracks_log'] = config.Path(optional=True)
        schema['crossfade'] = config.Boolean(optional=False)
        schema['playlist_url'] = config.String()
        schema['playlist'] = config.String()
        schema['cast_type'] = config.String()
        schema['link'] = config.String()
        schema['video_control'] = config.Boolean(optional=False)
        schema['refresh_playlists_rate'] = config.Integer(minimum=60)
        return schema

    def setup(self, registry):
        from .backend import MuzlabBackend
        from .core_event import MuzlabCoreEvent
        registry.add('backend', MuzlabBackend)
        registry.add('frontend', MuzlabCoreEvent)
        logger.info('Starting Mopidy-Muzlab %s' % self.version)
        send_states(self._state_uri, dict(current_version=self.version))


