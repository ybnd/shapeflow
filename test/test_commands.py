import abc
import shutil
import unittest
from unittest.mock import patch, Mock, call
from pathlib import Path
import argparse

import shapeflow.commands

import json
import socket
import requests
import shapeflow.main
import shapeflow.config


noop = lambda *x: None


@patch('shapeflow.commands.Command.__init__', noop)
class DoTest(unittest.TestCase):
    def test_valid_commands(self):
        for command in shapeflow.commands.__commands__:
            shapeflow.commands.do(command)

    def test_invalid_commands(self):
        self.assertRaises(ValueError, shapeflow.commands.do, 'sevre')
        self.assertRaises(ValueError, shapeflow.commands.do, '')
        self.assertRaises(ValueError, shapeflow.commands.do, 'dmp')
        self.assertRaises(ValueError, shapeflow.commands.do, 'nonexist')


class CommandTest(abc.ABC, unittest.TestCase):
    command: str

    def test_valid_command(self):
        self.assertTrue(self.command in shapeflow.commands.__commands__)

    def test_no_arguments(self):
        self.do()

    def do(self, args: shapeflow.commands.OptArgs = None):
        shapeflow.commands.do(self.command, args)


class ServeTest(CommandTest):
    command = 'serve'

    class MockMain(object):
        serve = noop

    class MockSock(object):
        __init__ = noop
        connect_ex = noop

    Main: Mock
    main: object
    serve: Mock

    @classmethod
    def setUpClass(cls) -> None:
        cls.Main = Mock(name='Main')
        cls.main = ServeTest.MockMain()
        cls.serve = Mock(name='serve')

        cls.main.serve = cls.serve
        cls.Main.return_value = cls.main

        shapeflow.main.Main = cls.Main

    def tearDown(self) -> None:
        self.Main.reset_mock()
        self.serve.reset_mock()

    def test_no_arguments(self):
        super().test_no_arguments()

        self.assertEqual(self.Main.call_count, 1)
        self.assertEqual(self.serve.call_count, 1)
        self.assertEqual(
            self.serve.call_args, call(host='127.0.0.1', port=7951, open=True)
        )

    def test_replace(self):
        sock = Mock(name='socket')
        connect_ex = Mock(name='connect_ex')
        post = Mock(name='post')

        sock.return_value.__enter__ = ServeTest.MockSock
        sock.return_value.__exit__ = noop
        ServeTest.MockSock.connect_ex = connect_ex
        connect_ex.side_effect = [0, 0, 1]  # todo: replace with actual return code
        post.return_value = None

        socket.socket = sock
        requests.post = post

        super().test_no_arguments()

        self.assertEqual(sock.call_count, 3)
        self.assertEqual(connect_ex.call_count, 3)
        self.assertEqual(post.call_count, 1)

        self.assertEqual(self.Main.call_count, 1)
        self.assertEqual(self.serve.call_count, 1)
        self.assertEqual(
            self.serve.call_args, call(host='127.0.0.1', port=7951, open=True)
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