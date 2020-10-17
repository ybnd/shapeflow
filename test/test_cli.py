import abc
import shutil
import unittest
from typing import List, Type
from unittest.mock import patch, Mock, call
from pathlib import Path
import argparse

import shapeflow.cli

import json
import socket
import requests
import argparse
import shapeflow.server
import shapeflow.config


def noop(*_, **__):
    pass


mock_Sf = Mock(name='Sf')


@patch('shapeflow.cli.Sf', mock_Sf)
class EntrypointTest(unittest.TestCase):
    def test_no_arguments(self):
        import os
        import sys
        import inspect

        # backwards import shenanigans
        current_dir = os.path.dirname(
            os.path.abspath(inspect.getfile(inspect.currentframe())))
        parent_dir = os.path.dirname(current_dir)
        sys.path.insert(0, parent_dir)

        import sf

        sf.main()

        self.assertEqual(1, mock_Sf.call_count)


@patch('shapeflow.server.ShapeflowServer.serve', noop)
@patch('argparse.ArgumentParser.exit', noop)
class SfTest(unittest.TestCase):
    def test_no_arguments(self):
        shapeflow.cli.Sf()

        # todo: assert things

    def test_help(self):
        shapeflow.cli.Sf(['--help'])

        # todo: assert things

    def test_version(self):
        shapeflow.cli.Sf(['--version'])

        # todo: assert things

    def test_valid_commands(self):
        for command in shapeflow.cli.Command:
            shapeflow.cli.Sf([str(command)])

    def test_invalid_commands(self):
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['sevre'])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, [''])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['dmp'])
        self.assertRaises(shapeflow.cli.CliError, shapeflow.cli.Sf, ['nope'])


class CommandTest(abc.ABC, unittest.TestCase):
    command: Type[shapeflow.cli.Command]
    mocks: List[Mock] = []

    def tearDown(self) -> None:
        for mock in self.mocks:
            mock.reset_mock()

    def test_valid_command(self):
        self.assertTrue(self.command in shapeflow.cli.Command)

    def test_no_arguments(self):
        self.command()

    def test_help(self):
        self.command(['--help'])


class MockServerInstance():
    serve = Mock(name='server.serve')


class MockServer():
    __new__ = Mock(name='__new__', return_value=MockServerInstance)


class MockSockInstance():
    connect_ex = Mock(name='connect_ex', side_effect=[0, 0, 1])


class MockSock():
    __init__ = noop
    __enter__ = Mock(name='__enter__', return_value=MockSockInstance)
    __exit__ = noop


class MockRequests():
    post = Mock(name='post', return_value=None)


@patch('shapeflow.server.ShapeflowServer', MockServer)
@patch('socket.socket', MockSock)
@patch('requests.post', MockRequests.post)
@patch('argparse.ArgumentParser.exit', noop)
class ServeTest(CommandTest):
    command = shapeflow.cli.Serve
    mocks = [
        MockServerInstance.serve,
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

        self.assertEqual(1, MockServerInstance.serve.call_count)
        self.assertEqual(
            call(host='127.0.0.1', port=7951, open=True),
            MockServerInstance.serve.call_args,
        )

    def test_valid_arguments(self):
        self.command(['--host', 'localhost', '--port', '1234', '--background'])

        self.assertEqual(3, MockSockInstance.connect_ex.call_count)
        self.assertEqual(1, MockRequests.post.call_count)

        self.assertEqual(1, MockServerInstance.serve.call_count)
        self.assertEqual(
            call(host='localhost', port=1234, open=False),
            MockServerInstance.serve.call_args,
        )


@patch('argparse.ArgumentParser.exit', noop)
class DumpTest(CommandTest):
    command = shapeflow.cli.Dump

    def test_no_arguments(self):
        super().test_no_arguments()

        # assertions go here

        Path('schemas.json').unlink()
        Path('settings.json').unlink()

    def test_dir(self):
        self.command(['stuff'])
        shutil.rmtree('stuff')

        # assertions go here


del CommandTest