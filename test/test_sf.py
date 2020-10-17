import sys
import subprocess
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, call
from shapeflow.util import ensure_path

with ensure_path(Path(__file__).parent.parent):
    import sf


mock_Sf = Mock(name='Sf')
@patch('shapeflow.cli.Sf', mock_Sf)
class EntrypointTest(unittest.TestCase):
    def test_no_arguments(self):
        sf.main()
        self.assertEqual(1, mock_Sf.call_count)
        self.assertEqual([], mock_Sf.call_args)


prog = [ sf.__file__ ]
class BootstrapVenvTest(unittest.TestCase):
    @staticmethod
    def fails_to_import():
        raise ModuleNotFoundError

    @staticmethod
    def imports_succesfully():
        pass

    def test_no_need(self):
        with patch.object(sys, 'argv', prog + ['serve']):
            sf._bootstrap_venv(self.imports_succesfully)

    @patch('subprocess.check_call')
    def test_bootstrap_success(self, mock_check_call):
        # fails first
        with patch.object(sys, 'argv', prog + ['serve']):
            sf._bootstrap_venv(self.fails_to_import)

        self.assertEqual(  # last three call arguments should match
            prog + ['serve', '--recursive-call'],
            mock_check_call.call_args.args[0][-3:]
        )

        # recovers
        with patch.object(sys, 'argv', prog + ['serve' '--recursive-call']):
            sf._bootstrap_venv(self.imports_succesfully)

    @patch('subprocess.check_call')
    def test_bootstrap_fail(self, mock_check_call):
        # fails first
        with patch.object(sys, 'argv', prog + ['serve']):
            sf._bootstrap_venv(self.fails_to_import)

        self.assertEqual(  # last three call arguments should match
            prog + ['serve', '--recursive-call'],
            mock_check_call.call_args.args[0][-3:]
        )

        # can't recover
        with patch.object(sys, 'argv', prog + ['serve', '--recursive-call']):
            self.assertRaises(
                SystemExit,
                sf._bootstrap_venv,
                self.fails_to_import
            )

    @patch('subprocess.check_call')
    def test_keyboardinterrupt(self, mock_check_call):
        # pass through to finish execution & join initial call
        mock_check_call.side_effect = KeyboardInterrupt
        with patch.object(sys, 'argv', prog + ['serve']):
            sf._bootstrap_venv(self.fails_to_import)

    @patch('subprocess.check_call')
    def test_calledprocesserror(self, mock_check_call):
        # exit with the correct exit code if the subprocess fails
        mock_check_call.side_effect = subprocess.CalledProcessError(17, '')

        with self.assertRaises(SystemExit) as e:
            with patch.object(sys, 'argv', prog + ['serve']):
                sf._bootstrap_venv(self.fails_to_import)

        self.assertEqual(17, e.exception.code)

    @patch('subprocess.check_call')
    def test_catchall_exception(self, mock_check_call):
        # re-raise any other exceptions
        mock_check_call.side_effect = Exception

        with self.assertRaises(Exception):
            with patch.object(sys, 'argv', prog + ['serve']):
                sf._bootstrap_venv(self.fails_to_import)
