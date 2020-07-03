import os
import shutil
import unittest
from contextlib import contextmanager

import time
import copy
import json
from threading import Thread


HOST = "127.0.0.1"
PORT = str(7845)

__VIDEO__ = 'test.mp4'
__DESIGN__ = 'test.svg'

# Point to right files in Travis CI build
if os.getcwd() == '/home/travis/build/ybnd/isimple':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__


@contextmanager
def application(keep: bool = False):
    from isimple import settings, ROOTDIR, save_settings

    CACHE = os.path.join(ROOTDIR, 'test_main-cache')
    DB = os.path.join(ROOTDIR, 'test_main-history.db')
    STATE = os.path.join(ROOTDIR, 'test_main-state')
    RESULTS = os.path.join(ROOTDIR, 'test_main-results')

    def _clear():
        if not keep:
            if os.path.exists(CACHE):
                shutil.rmtree(CACHE)
            if os.path.exists(DB):
                os.remove(DB)
            if os.path.exists(STATE):
                os.remove(STATE)
            if os.path.exists(RESULTS):
                shutil.rmtree(RESULTS)

    _clear()

    try:
        with settings.cache.override({"dir": CACHE, "do_cache": False, "do_background": False}), \
                settings.db.override({"path": DB}), \
                settings.app.override({"state_path": STATE, "save_result": 'in result directory', "result_dir": RESULTS}), \
                settings.log.override({'lvl_console': 'debug', 'lvl_file': 'debug'}):
            save_settings(settings)

            # import from isimple.main here -> current settings are respected
            import isimple.main
            import isimple.db

            main = isimple.main.Main()
            main._history = isimple.db.History(settings.db.path)
            main._app.testing = True
            client = main._app.test_client()

            yield main, client, settings
    finally:
        save_settings(settings)

        # Explicitly remove any leftover analyzers
        app_state = json.loads(client.get('/api/app_state').data)
        for id in app_state['ids']:
            client.post(f'/api/{id}/remove')

        del main
        del settings
        _clear()


class MainTest(unittest.TestCase):
    """Test Main methods -- global"""
    def test_schemas(self):
        with application() as (server, client, settings):
            # Test 'legal' options
            for for_type in ['state', 'analyzer', 'feature',
                             'frame_interval_setting', 'filter', 'transform',
                             'paths', 'config']:
                r = client.get(f'/api/options/{for_type}')
                self.assertEqual(200, r.status_code)
                self.assertLess(0, len(r.data))

            # Test 'illegal' options
            for for_type in ['slate', '', '1234564523786']:
                try:
                    client.get(f'/api/options/{for_type}')
                except ValueError:
                    pass

            # Test settings_schema
            r = client.get('/api/settings_schema')
            self.assertEqual(200, r.status_code)
            self.assertEqual(settings.schema(), json.loads(r.data))

    def test_file_checks(self):
        with application() as (server, client, settings):
            # Check real files
            self.assertEqual(
                True,
                json.loads(
                    client.put(
                        '/api/check_design_path',
                        data=json.dumps({"design_path": __DESIGN__})
                    ).data
                )
            )
            self.assertEqual(
                True,
                json.loads(
                    client.put(
                        '/api/check_video_path',
                        data=json.dumps({"video_path": __VIDEO__})
                    ).data
                )
            )

            # Check wrong real files
            self.assertEqual(
                True,  # OnionSVG.check_svg() checks if directory contains <file>.svg if extension doesn't match
                json.loads(
                    client.put(
                        '/api/check_design_path',
                        data=json.dumps({"design_path": __VIDEO__})
                    ).data
                )
            )
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/check_video_path',
                        data=json.dumps({"video_path": __DESIGN__})
                    ).data
                )
            )

            # Check fake files
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/check_design_path',
                        data=json.dumps({"design_path": "test1.svg"})
                    ).data
                )
            )
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/check_video_path',
                        data=json.dumps({"video_path": "test2.mp4"})
                    ).data
                )
            )

    def test_log_stream(self):
        with application() as (server, client, settings):
            class LogStreamThread(Thread):
                def run(self):
                    self._data = client.get('/api/get_log').data

            thread = LogStreamThread()
            thread.start()

            client.get('/api/ping')
            client.get('/api/ping')

            time.sleep(1)

            client.put('/api/stop_log')

            thread.join()
            self.assertEqual(
                2,
                thread._data.count(b'received ping')
            )


class MainAnalyzerTest(unittest.TestCase):
    """Test Main methods -- VideoAnalyzer interaction"""

    CONFIG = {
        "video_path": __VIDEO__,
        "design_path": __DESIGN__,
        "features": [''],
        "parameters": [None],  # todo: parameters should be resolved to the same length as features, for now _get_featuresets() fails ~ zip(features, parameters)
        "frame_interval_setting": 'Nf',
        'Nf': 5,
    }
    ROI = {
        'BL': {'x': 0.8187, 'y': 0.2389},
        'TL': {'x': 0.8141, 'y': 0.8917},
        'TR': {'x': 0.2328, 'y': 0.8944},
        'BR': {'x': 0.2313, 'y': 0.2361}
    }
    HIT_FRAME = 16
    TRUE_HITS = [
        # (relative_x, relative_y)
        (0.37, 0.29),
        (0.78, 0.68),
    ]
    FAKE_HITS = [
        (0.20, 0.47),
        (0.88, 0.44),
    ]
    MISSES = [
        (0.05, 0.05),
        (0.95, 0.95),
    ]
    DOUBLE_HITS = [
        (0.29, 0.83),
    ]

    def test_analyzer(self):
        with application() as (server, client, settings):
            r = client.post('/api/init')
            self.assertEqual(200, r.status_code)

            id = json.loads(r.data)
            self.assertNotEqual('', id)

            self.assertIn(id, server._roots)
            self.assertFalse(
                json.loads(client.get(f'/api/{id}/can_launch').data)
            )

            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.get(f'/api/{id}/can_launch').data)
            )
            self.assertTrue(
                json.loads(client.post(f'/api/{id}/launch').data)
            )
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": {"transform": {"roi": None}}})
            )

            # Can't analyze yet since transform.roi is not set
            self.assertRaises(AttributeError, client.post, f'/api/{id}/call/analyze')

            self.assertTrue(
                server._roots[id].results[server._roots[id].config.features[0]].isna().all().all()
            )

            client.post(
                f'/api/{id}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            self.assertEqual(
                self.ROI,
                server._roots[id].transform.config.roi
            )

            client.post(f'/api/{id}/call/analyze')

            self.assertFalse(
                server._roots[id].results[
                    server._roots[id].config.features[0]].isna().all().all()
            )

            client.post(f'/api/{id}/remove')
            self.assertNotIn(id, server._roots)

    def test_analyzer_roi_flip(self):
        with application() as (server, client, settings):
            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')

            client.post(
                f'/api/{id}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({ "config": {"transform":
                    {"flip": {"horizontal": True, "vertical": True}}}})
            )

            self.assertEqual(
                {"horizontal": True, "vertical": True},
                server._roots[id].transform.config.flip.to_dict()
            )

            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": {"transform":
                    {"flip": {"horizontal": False}}}})
            )

            # Previous value of transform.flip.vertical should still be remembered
            self.assertEqual(
                {"horizontal": False, "vertical": True},
                server._roots[id].transform.config.flip.to_dict()
            )

    def test_analyzer_filter_click(self):
        with application() as (server, client, settings):
            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')
            client.post(
                f'/api/{id}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            for click in self.MISSES:
                r = client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertEqual({}, json.loads(r.data))

            for click in self.FAKE_HITS:
                r = client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertEqual({}, json.loads(r.data))

            for click in self.TRUE_HITS:
                r = client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertIn('color', json.loads(r.data))

            for click in self.DOUBLE_HITS:
                r = client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps(
                        {'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertIn('message', json.loads(r.data))

    def test_analyzer_history(self):
        with application() as (server, client, settings):
            id1 = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id1}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id1}/launch')
            client.post(
                f'/api/{id1}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            client.post(f'/api/{id1}/remove')

            id2 = json.loads(client.post('/api/init').data)

            self.assertNotEqual(id1, id2)

            client.post(
                f'/api/{id2}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.get(f'/api/{id2}/can_launch').data)
            )
            self.assertTrue(
                json.loads(client.post(f'/api/{id2}/launch').data)
            )
            self.assertEqual(
                self.ROI,
                json.loads(
                    client.get(f'/api/{id2}/call/get_config'
                ).data)['transform']['roi']
            )

    # @unittest.skip('to be fixed!')
    def test_analyzer_undo_redo_roi(self):
        with application() as (server, client, settings):
            ROI_SEQUENCE = [
                {
                    'BL': {'x': 0.1, 'y': 0.2389},
                    'TL': {'x': 0.8141, 'y': 0.8917},
                    'TR': {'x': 0.2328, 'y': 0.8944},
                    'BR': {'x': 0.2313, 'y': 0.2361}
                },
                {
                    'BL': {'x': 0.2, 'y': 0.2389},
                    'TL': {'x': 0.8141, 'y': 0.8917},
                    'TR': {'x': 0.2328, 'y': 0.8944},
                    'BR': {'x': 0.2313, 'y': 0.2361}
                },
                {
                    'BL': {'x': 0.3, 'y': 0.2389},
                    'TL': {'x': 0.8141, 'y': 0.8917},
                    'TR': {'x': 0.2328, 'y': 0.8944},
                    'BR': {'x': 0.2313, 'y': 0.2361}
                },
                {
                    'BL': {'x': 0.4, 'y': 0.2389},
                    'TL': {'x': 0.8141, 'y': 0.8917},
                    'TR': {'x': 0.2328, 'y': 0.8944},
                    'BR': {'x': 0.2313, 'y': 0.2361}
                },
            ]

            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')

            for ROI in ROI_SEQUENCE:
                client.post(
                    f'/api/{id}/call/estimate_transform',
                    data=json.dumps({"roi": ROI})
                )
                # client.post(f'/api/{id}/call/commit')

            for ROI in ROI_SEQUENCE[::-1]:
                self.assertEqual(
                    ROI,
                    json.loads(
                        client.get(f'/api/{id}/call/get_config'
                    ).data)['transform']['roi']
                )
                client.post(f'/api/{id}/call/undo_config')

            for ROI in ROI_SEQUENCE:
                client.post(f'/api/{id}/call/redo_config')
                self.assertEqual(
                    ROI,
                    json.loads(
                        client.get(f'/api/{id}/call/get_config'
                    ).data)['transform']['roi']
                )

    def test_analyzers_queue_ops(self):
        with application() as (server, client, settings):
            id1 = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id1}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id1}/launch')
            client.post(
                f'/api/{id1}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            id2 = json.loads(client.post('/api/init').data)

            client.post(
                f'/api/{id2}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.post(f'/api/{id2}/launch').data)
            )
            client.post(
                f'/api/{id2}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            id3 = json.loads(client.post('/api/init').data)

            client.post(
                f'/api/{id3}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.post(f'/api/{id3}/launch').data)
            )
            client.post(
                f'/api/{id3}/call/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            app_state = json.loads(client.get('/api/app_state').data)
            self.assertEqual(
                0,  # QueueState.STOPPED
                app_state['q_state']
            )

            # Start queue in separate thread (don't block until done)
            thread = Thread(
                target=client.post,
                args=['/api/start'],
                kwargs={'data': json.dumps({'queue': [id1, id2, id3]})}
            )
            thread.start()

            # Stop queue while not done yet
            client.post('/api/stop')
            thread.join()

            app_state = json.loads(client.get('/api/app_state').data)
            self.assertEqual(
                0,  # QueueState.STOPPED
                app_state['q_state']
            )
            self.assertLess(
                0.95,  # id1 should be ~ done, not 100% due to requested_frames
                app_state['status'][app_state['ids'].index(id1)]['progress']
            )

            self.assertEqual(
                7, # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id1)]['state']
            )
            self.assertNotEqual(
                7,  # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id2)]['state']
            )
            self.assertNotEqual(
                7,  # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id3)]['state']
            )

            # Start the queue again and block until done
            client.post('/api/start', data=json.dumps({'queue': [id3, id2, id1]}))

            app_state = json.loads(client.get('/api/app_state').data)
            self.assertEqual(
                0,  # QueueState.STOPPED
                app_state['q_state']
            )

            self.assertEqual(
                7, # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id1)]['state']
            )
            self.assertEqual(
                7,  # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id2)]['state']
            )
            self.assertEqual(
                7,  # AnalyzerState.DONE
                app_state['status'][app_state['ids'].index(id3)]['state']
            )

    @unittest.skip('placeholder')
    def test_image_streaming(self):
        raise NotImplementedError

    @unittest.skip('placeholder')
    def test_json_streaming(self):
        raise NotImplementedError


if __name__ == '__main__':
    unittest.main()

