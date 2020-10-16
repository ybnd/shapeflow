import abc
import shutil
import unittest
from typing import List
from unittest.mock import patch, Mock, call
from pathlib import Path
import argparse

import shapeflow.cli

import json
import socket
import requests
import shapeflow.main
import shapeflow.config


noop = lambda *x: None


@patch('shapeflow.commands.Command.__init__', noop)
class DoTest(unittest.TestCase):
    def test_valid_commands(self):
        for command in shapeflow.cli.__commands__:
            shapeflow.cli.do(command)

    def test_invalid_commands(self):
        self.assertRaises(ValueError, shapeflow.cli.do, 'sevre')
        self.assertRaises(ValueError, shapeflow.cli.do, '')
        self.assertRaises(ValueError, shapeflow.cli.do, 'dmp')
        self.assertRaises(ValueError, shapeflow.cli.do, 'nonexist')


class CommandTest(abc.ABC, unittest.TestCase):
    command: str
    mocks: List[Mock] = []

    def tearDown(self) -> None:
        for mock in self.mocks:
            mock.reset_mock()

    def test_valid_command(self):
        self.assertTrue(self.command in shapeflow.cli.__commands__)

    def test_no_arguments(self, *args):
        self.do()

    def do(self, args: shapeflow.cli.OptArgs = None):
        shapeflow.cli.do(self.command, args)



class MockMainInstance():
    serve = Mock(name='main.serve')


class MockMain():
    __new__ = Mock(name='__new__', return_value=MockMainInstance)


class MockSockInstance():
    connect_ex = Mock(name='connect_ex', side_effect=[0, 0, 1])


class MockSock():
    __init__ = noop
    __enter__ = Mock(name='__enter__', return_value=MockSockInstance)
    __exit__ = noop


class MockRequests():
    post = Mock(name='post', return_value=None)


@patch('shapeflow.main.Main', MockMain)
@patch('socket.socket', MockSock)
@patch('requests.post', MockRequests.post)
class ServeTest(CommandTest):
    command = 'serve'
    mocks = [
        MockMainInstance.serve,
        MockSockInstance.connect_ex,
        MockRequests.post,
    ]

    def tearDown(self) -> None:
        super().tearDown()
        MockSockInstance.connect_ex.side_effect = [0, 0, 1]  # explicitly :(

    def test_no_arguments(self):
        super().test_no_arguments()

        self.assertEqual(3, MockSockInstance.connect_ex.call_count)
        self.assertEqual(1, MockRequests.post.call_count)

        self.assertEqual(1, MockMainInstance.serve.call_count)
        self.assertEqual(
            call(host='127.0.0.1', port=7951, open=True),
            MockMainInstance.serve.call_args,
        )

    def test_valid_arguments(self):
        self.do(['--host', 'localhost', '--port', '1234', '--background'])

        self.assertEqual(3, MockSockInstance.connect_ex.call_count)
        self.assertEqual(1, MockRequests.post.call_count)

        self.assertEqual(1, MockMainInstance.serve.call_count)
        self.assertEqual(
            call(host='localhost', port=1234, open=False),
            MockMainInstance.serve.call_args,
        )


class DumpTest(CommandTest):
    command = 'dump'

    def test_no_arguments(self):
        super().test_no_arguments()

        # assertions go here

        Path('schemas.json').unlink()
        Path('settings.json').unlink()

    def test_dir(self):
        self.do(['stuff'])
        shutil.rmtree('stuff')

        # assertions go here


del CommandTest