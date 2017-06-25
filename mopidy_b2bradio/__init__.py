# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

import logging

from mopidy import config, ext


__version__ = '0.1.0'

logger = logging.getLogger(__name__)

class B2bradioExtension(ext.Extension):

    dist_name = 'Mopidy-B2bradio'
    ext_name = 'b2bradio'
    version = __version__

    def get_default_config(self):
        conf_file = os.path.join(os.path.dirname(__file__), 'ext.conf')
        return config.read(conf_file)

    def get_config_schema(self):
        schema = super(B2bradioExtension, self).get_config_schema()
        schema['base_dir'] = config.Path(optional=True)
        schema['default_encoding'] = config.String()
        schema['default_extension'] = config.String(choices=['.m3u', '.m3u8'])
        schema['playlists_dir'] = config.Path(optional=True)
        schema['playlist'] = config.String()
        schema['playlist_url'] = config.String()
        schema['refresh_playlists_rate'] = config.Integer(minimum=60)
        return schema

    def setup(self, registry):
        from .backend import B2bradioBackend
        from .core_event import B2bradioCoreEvent
        registry.add('backend', B2bradioBackend)
        registry.add('frontend', B2bradioCoreEvent)
