import os
from pathlib import Path
import shutil
import importlib
import abc
from typing import List
import subprocess
from contextlib import contextmanager
import unittest
from unittest.mock import patch, Mock


import os
import sys
import inspect

# backwards import shenanigans
current_dir = os.path.dirname(
    os.path.abspath(inspect.getfile(inspect.currentframe())))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

import sf
import shapeflow.commands


class SfTest(unittest.TestCase):  # todo: inspect print?
    do: Mock = Mock(name='do')

    @classmethod
    def setUpClass(cls) -> None:
        cls.commands = shapeflow.commands.__commands__
        shapeflow.commands.do = cls.do

    def tearDown(self) -> None:
        self.do.reset_mock()

    def test_sf_help(self):
        with patch.object(sys, 'argv', ['sf.py', '--help']):
            sf.main()
            self.assertFalse(self.do.called)

    def test_sf_version(self):
        with patch.object(sys, 'argv', ['sf.py', '--version']):
            sf.main()
            self.assertFalse(self.do.called)

    def test_sf_default_command(self):
        sf.main()
        self.do.assert_called_once_with('serve', [])

    def test_sf_command(self):
        for c in self.commands:
            with self.subTest(c), patch.object(sys, 'argv', ['sf.py', c]):
                sf.main()
                self.do.assert_called_once_with(c, [])
                self.do.reset_mock()

    def test_sf_help_command(self):
        for c in self.commands:
            with self.subTest(c), patch.object(sys, 'argv', ['sf.py', '--help', c]):
                sf.main()
                self.assertFalse(self.do.called)
