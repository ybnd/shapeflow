import os
import unittest
from contextlib import contextmanager

import time
import subprocess

from isimple import settings, ROOTDIR, save_settings


@unittest.skip("placeholder")
class MainTest(unittest.TestCase):
    """Test Main methods -- global"""
    def test_serve(self):
        raise NotImplementedError

    def test_schemas(self):
        raise NotImplementedError

    def test_file_selection(self):  # todo: may be tricky to test properly
        raise NotImplementedError

    def test_settings(self):
        raise NotImplementedError

    def test_log_stream(self):
        raise NotImplementedError


@unittest.skip("placeholder")
class MainAnalyzerTest(unittest.TestCase):
    """Test Main methods -- VideoAnalyzer interaction"""
    def test_call_endpoints(self):
        raise NotImplementedError

    def test_call_endpoints_malformed(self):
        raise NotImplementedError

    def test_analyzer(self):
        raise NotImplementedError

    def test_analyzer_roi(self):
        raise NotImplementedError

    def test_analyzer_from_history(self):
        raise NotImplementedError

    def test_analyzer_undo_redo(self):
        raise NotImplementedError

    def test_analyzers_queue_ops(self):
        raise NotImplementedError

    def test_image_streaming(self):
        raise NotImplementedError

    def test_json_streaming(self):
        raise NotImplementedError

    def test_app_state(self):
        raise NotImplementedError


if __name__ == '__main__':
    unittest.main()

