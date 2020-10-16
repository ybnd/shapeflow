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
import shapeflow.cli


do = Mock(name='do')


@patch('shapeflow.commands.do', do)
class SfTest(unittest.TestCase):  # todo: inspect print?
    @classmethod
    def setUpClass(cls) -> None:
        cls.commands = shapeflow.cli.__commands__

    def tearDown(self) -> None:
        do.reset_mock()

    def test_sf_help(self):
        with patch.object(sys, 'argv', ['sf.py', '--help']):
            sf.main()
            self.assertFalse(do.called)

    def test_sf_version(self):
        with patch.object(sys, 'argv', ['sf.py', '--version']):
            sf.main()
            self.assertFalse(do.called)

    def test_sf_default_command(self):
        sf.main()
        do.assert_called_once_with('serve', [])

    def test_sf_command(self):
        for c in self.commands:
            with self.subTest(c), patch.object(sys, 'argv', ['sf.py', c]):
                sf.main()
                do.assert_called_once_with(c, [])
                do.reset_mock()

    def test_sf_help_command(self):
        for c in self.commands:
            with self.subTest(c), patch.object(sys, 'argv', ['sf.py', '--help', c]):
                sf.main()
                self.assertFalse(do.called)
