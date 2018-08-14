import pytest
import mock
from mopidy import core
from mopidy_muzlab import MuzlabExtension, backend
from mopidy_muzlab.backend import MuzlabBackend

def test_init_backend(backend_mock):
    assert backend_mock

def test_backend_start(backend_mock):
	assert backend_mock.on_start()

def test_backend_stop(backend_mock):
	assert backend_mock.on_stop()

def test_init_frontend(frontend_mock):
    assert frontend_mock

def test_frontend_start(frontend_mock):
	assert frontend_mock.on_start()

def test_frontend_stop(frontend_mock):
	assert frontend_mock.on_stop()


        