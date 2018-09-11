import pytest
import mock
from mopidy import core
from mopidy_muzlab import MuzlabExtension, backend
from mopidy_muzlab.backend import MuzlabBackend

def test_init_backend(fake_backend):
    assert fake_backend

def test_backend_start(fake_backend):
	assert fake_backend.on_start()

def test_backend_stop(fake_backend):
	assert fake_backend.on_stop()

def test_init_frontend(fake_frontend):
    assert fake_frontend

def test_frontend_start(fake_frontend):
	assert fake_frontend.on_start()

def test_frontend_stop(fake_frontend):
	assert fake_frontend.on_stop()


        