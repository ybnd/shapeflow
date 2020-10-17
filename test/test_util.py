import unittest
from unittest.mock import patch

import os
import json
import tkinter
import tkinter.filedialog
import subprocess

from typing import _GenericAlias, Union, Tuple, List, Dict, Optional  #type: ignore

from shapeflow.util.meta import resolve_type_to_most_specific
from shapeflow.config import VideoAnalyzerConfig

from shapeflow.util.filedialog import _Tkinter, _Zenity


class ResolveTypeTest(unittest.TestCase):
    def test_specifiable_union(self):
        class MockType(object):
            pass

        class SpecificMockType(MockType):
            pass

        self.assertEqual(
            SpecificMockType,
            resolve_type_to_most_specific(
                Union[SpecificMockType, MockType, None]
            )
        )
        self.assertEqual(
            Tuple[List[Dict[str,SpecificMockType]],...],
            resolve_type_to_most_specific(
                Tuple[List[Dict[str,Union[SpecificMockType, MockType, None]]],...]
            )
        )

    def test_unspecifiable_union(self):
        self.assertEqual(
            dict,
            resolve_type_to_most_specific(
                Union[dict, str, int]
            )
        )
        self.assertEqual(
            Tuple[List[Dict[str, dict]],...],
            resolve_type_to_most_specific(
                Tuple[List[Dict[str, Union[dict, str, int]]],...]
            )
        )


class FileDialogTest(unittest.TestCase):
    kw = [
        'title',
        'pattern',
        'pattern_description',
    ]
    kwargs = {k:k for k in kw}

    @patch('tkinter.filedialog.askopenfilename')
    def test_tkinter_load(self, askopenfilename):
        _Tkinter().load(**self.kwargs)

        self.assertEqual(
            {v:k for k,v in _Tkinter._map.items()},
            askopenfilename.call_args[1]
        )

    @patch('tkinter.filedialog.asksaveasfilename')
    def test_tkinter_save(self, asksaveasfilename):
        _Tkinter().save(**self.kwargs)

        self.assertEqual(
            {v:k for k,v in _Tkinter._map.items()},
            asksaveasfilename.call_args[1]
        )

    @patch('subprocess.Popen')
    def test_zenity_load(self, Popen):
        Popen.return_value.communicate.return_value = (b'', 0)
        _Zenity().load(**self.kwargs)

        c = 'zenity --file-selection --title title --file-filter pattern'

        self.assertEqual(
            sorted(c.split(' ')),
            sorted(Popen.call_args[0][0])
        )

    @patch('subprocess.Popen')
    def test_zenity_save(self, Popen):
        Popen.return_value.communicate.return_value = (b'', 0)
        _Zenity().save(**self.kwargs)

        c = 'zenity --file-selection --save --title title --file-filter pattern'

        self.assertEqual(
            sorted(c.split(' ')),
            sorted(Popen.call_args[0][0])
        )
