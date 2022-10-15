import os
import shutil
import unittest
from unittest.mock import patch
from contextlib import contextmanager

import time
import json
import subprocess

import flask
from flask.testing import FlaskClient

from shapeflow import settings, ROOTDIR, save_settings
from shapeflow.server import ShapeflowServer, UI, DIST

CACHE = os.path.join(ROOTDIR, 'test_main-cache')
DB = os.path.join(ROOTDIR, 'test_main-history.db')
STATE = os.path.join(ROOTDIR, 'test_main-state')
SETTINGS = os.path.join(ROOTDIR, 'settings')

HOST = "127.0.0.1"
PORT = 7951



def api(*args):
    return "/".join([f"http://{HOST}:{PORT}/api"] + list(args))


def get(url):
    with subprocess.Popen(['curl', '-X', 'GET', url], stdout=subprocess.PIPE) as p:
        response, error = p.communicate()
    return response


def post(url, data=None):
    if data is None:
        with subprocess.Popen(['curl', '-X', 'POST', url], stdout=subprocess.PIPE) as p:
            response, error = p.communicate()
    else:
        with subprocess.Popen(['curl', '-X', 'POST', url, '--header', "Content-Type: application/json", '--data', data], stdout=subprocess.PIPE) as p:
            response, error = p.communicate()
    return response


def start_server():
    return subprocess.Popen(
        ['python', 'sf.py', 'serve', '--background', '--host', HOST, '--port', str(PORT)],
        cwd='..'
    )

@contextmanager
def override_settings():
    # Clean up after previous runs (just in case)
    if os.path.exists(CACHE):
        shutil.rmtree(CACHE)
    if os.path.exists(DB):
        os.remove(DB)
    if os.path.exists(STATE):
        os.remove(STATE)

    try:
        with settings.cache.override({"dir": CACHE}), \
                settings.db.override({"path": DB}), \
                settings.app.override({"state_path": STATE}):
            save_settings()
            yield
    finally:
        save_settings()

        if os.path.exists(CACHE):
            shutil.rmtree(CACHE)
        if os.path.exists(DB):
            os.remove(DB)
        if os.path.exists(STATE):
            os.remove(STATE)

@unittest.skip("Unreliable")
class ServerTest(unittest.TestCase):
    def setUp(self) -> None:
        r = post(api('quit'))
        if r:
            time.sleep(5)

    def tearDown(self) -> None:
        r = post(api('quit'))
        if r:
            time.sleep(5)

    """Test server-level methods"""
    def test_startup(self):
        with override_settings():
            # Server is down, no response
            self.assertEqual(b'', get(api('ping')))

            # Start server & wait a bit
            start_server()
            time.sleep(5)

            # Server is up, some response
            self.assertNotEqual(b'', get(api('ping')))

            # Quit server & wait a bit
            post(api('quit'))
            time.sleep(5)

            # Server is down, no response again
            self.assertEqual(b'', get(api('ping')))

    def test_unload_shutdown(self):
        with override_settings():
            # Start server & wait a bit
            start_server()
            time.sleep(5)

            # Server is up, some response
            self.assertNotEqual(b'', get(api('ping')))

            # Post unload trigger
            post(api('unload'))

            # Wait for 10 seconds, server should have quit
            time.sleep(10)
            self.assertEqual(b'', get(api('ping')))

    def test_unload_keepup(self):
        with override_settings():
            # Start server & wait a bit
            start_server()
            time.sleep(5)

            # Server is up, some response
            self.assertNotEqual(b'', get(api('ping')))

            # Post unload trigger
            post(api('unload'))

            # Wait for 1 seconds, server should still be up
            time.sleep(1)
            self.assertNotEqual(b'', get(api('ping')))

            # Wait for 10 seconds, server should still be up
            time.sleep(10)
            self.assertNotEqual(b'', get(api('ping')))

    def test_set_settings_restart(self):
        with override_settings():
            # Start server & wait a bit
            p = start_server()
            time.sleep(5)

            # Server is up, some response
            self.assertNotEqual(b'', get(api('ping')))

            first_pid = get(api('pid_hash'))
            first_settings = json.loads(get(api('get_settings')))

            # Post set_settings trigger & wait a bit
            post(api('set_settings'), data=json.dumps({'settings': {'log': {'keep': 0}}}))
            time.sleep(10)

            # Server is up on the same address, some response
            self.assertNotEqual(b'', get(api('ping')))
            second_settings = json.loads(get(api('get_settings')))

            # Server is on a different PID
            self.assertNotEqual(first_pid, get(api('pid_hash')))

            # second_settings.log.keep == 0
            self.assertEqual(0, second_settings['log']['keep'])

            # Set settings gack to first_settings
            post(api('set_settings'), data=json.dumps({'settings': first_settings}))
            time.sleep(10)


@patch('os.path.isfile')
@patch('flask.send_from_directory')
@patch('os.path.isdir', lambda _: True)
@patch('os.listdir', lambda _: ['index.html'])
class FlaskTest(unittest.TestCase):
    client: FlaskClient

    def setUp(self) -> None:
        sfs = ShapeflowServer()
        sfs._app.config['TESTING'] = True

        self.client = sfs._app.test_client()

    def test_serve_index_200(self, send_from_directory, isfile):
        isfile.return_value = True
        send_from_directory.return_value = flask.Response()

        r = self.client.get('/')

        send_from_directory.assert_called_with(DIST, 'index.html')
        self.assertEqual(r.status_code, 200)

    def test_serve_index_404(self, send_from_directory, isfile):
        isfile.return_value = False
        send_from_directory.return_value = flask.Response()

        r = self.client.get('/')

        send_from_directory.assert_called_with(UI, '404.html')
        self.assertEqual(r.status_code, 404)

    def test_serve_file_200(self, send_from_directory, isfile):
        isfile.return_value = True
        send_from_directory.return_value = flask.Response()

        r = self.client.get('/something.txt')

        send_from_directory.assert_called_with(DIST, 'something.txt')
        self.assertEqual(r.status_code, 200)

    def test_serve_file_404(self, send_from_directory, isfile):
        isfile.return_value = False
        send_from_directory.return_value = flask.Response()

        r = self.client.get('/something.txt')

        send_from_directory.assert_not_called()
        self.assertEqual(r.status_code, 404)


if __name__ == '__main__':
    unittest.main()
