import unittest
from unittest.mock import patch

import os
import json
import tkinter
import tkinter.filedialog
import subprocess


from shapeflow.util.filedialog import _Tkinter, _Zenity
from shapeflow.util.from_venv import _VenvCall, _WindowsVenvCall, from_venv

from shapeflow.util.filedialog import _Tkinter, _Zenity


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


ENV = '.venv-name'
PYTHON = 'python4.2.0'
@patch('os.path.isfile')
@patch('os.path.isdir')
class FromVenvTest(unittest.TestCase):
    @patch('subprocess.check_call')
    def test_from_venv_success(self, check_call, isdir, isfile):
        # Should just pass
        check_call.return_value = None
        isdir.return_value = True
        isfile.return_value = True
        from_venv(ENV)

    @patch('subprocess.check_call')
    def test_from_venv_keyboardinterrupt(self, check_call, isdir, isfile):
        # Should just pass
        check_call.side_effect = KeyboardInterrupt
        isdir.return_value = True
        isfile.return_value = True
        from_venv(ENV)

    @patch('subprocess.check_call')
    def test_from_venv_fail_calledprocesserror(self, check_call, isdir, isfile):
        # Should SystemExit with the same exit code as the subprocess
        check_call.side_effect = subprocess.CalledProcessError(17, '...')
        isdir.return_value = True
        isfile.return_value = True

        with self.assertRaises(SystemExit) as e:
            from_venv(ENV)

        self.assertEqual(17, e.exception.code)

    @patch('subprocess.check_call')
    def test_from_venv_fail_exception(self, check_call, isdir, isfile):
        # Just error out with the same exception
        class SomeException(Exception):
            pass

        check_call.side_effect = SomeException
        isdir.return_value = True
        isfile.return_value = True

        with self.assertRaises(SomeException):
            from_venv(ENV)

@patch('os.path.isfile')
@patch('os.path.isdir')
class VenvCallTest(unittest.TestCase):
    # _VenvCall tests
    def test_venv_call_first_try(self, isdir, isfile):
        # First option should succeed
        isdir.return_value = True
        isfile.return_value = True

        command, shell = _VenvCall(ENV, PYTHON).resolve()

        self.assertIn(ENV, command[0])
        self.assertIn(PYTHON, command[0])
        self.assertIn(_VenvCall.subpath, command[0])
        self.assertEqual(False, shell)

    def test_venv_call_third_try(self, isdir, isfile):
        # First option does not exist due missing binary
        # Should succeed on second fallback python candidate
        isdir.return_value = True
        isfile.side_effects = [False, False, True]

        command, shell = _VenvCall(ENV, PYTHON).resolve()

        self.assertIn(ENV, command[0])
        self.assertIn(_VenvCall.pythons[1], command[0])
        self.assertIn(_VenvCall.subpath, command[0])
        self.assertEqual(False, shell)

    def test_venv_call_directory_fail(self, isdir, isfile):
        # Environment directory is missing
        # Should fail
        isdir.return_value = False
        isfile.return_value = True

        self.assertRaises(
            EnvironmentError, _VenvCall(ENV, PYTHON).resolve
        )

    def test_venv_call_binary_fail(self, isdir, isfile):
        # None of the candidate binaries exist
        # Should fail
        isdir.return_value = True
        isfile.return_value = False

        self.assertRaises(
            EnvironmentError, _VenvCall(ENV, PYTHON).resolve
        )

    # _WindowsVenvCall tests
    def test_windows_venv_call_first_try(self, isdir, isfile):
        # First option should succeed
        isdir.return_value = True
        isfile.return_value = True

        command, shell = _WindowsVenvCall(ENV, PYTHON).resolve()

        self.assertIn(ENV, command[0])
        self.assertIn(PYTHON, command[0])
        self.assertIn(_WindowsVenvCall.subpath, command[0])
        self.assertEqual(True, shell)

    def test_windows_venv_call_third_try(self, isdir, isfile):
        # First option does not exist due missing binary
        # Should succeed on second fallback python candidate
        isdir.return_value = True
        isfile.side_effects = [False, False, True]

        command, shell = _WindowsVenvCall(ENV, PYTHON).resolve()

        self.assertIn(ENV, command[0])
        self.assertIn(_WindowsVenvCall.pythons[1], command[0])
        self.assertIn(_WindowsVenvCall.subpath, command[0])
        self.assertEqual(True, shell)

    def test_windows_venv_call_directory_fail(self, isdir, isfile):
        # Environment directory is missing
        # Should fail
        isdir.return_value = False
        isfile.return_value = True

        self.assertRaises(
            EnvironmentError, _WindowsVenvCall(ENV, PYTHON).resolve
        )

    def test_windows_venv_call_binary_fail(self, isdir, isfile):
        # None of the candidate binaries exist
        # Should fail
        isdir.return_value = True
        isfile.return_value = False

        self.assertRaises(
            EnvironmentError, _WindowsVenvCall(ENV, PYTHON).resolve
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
