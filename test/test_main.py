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

from isimple import ROOTDIR


CACHE = os.path.join(ROOTDIR, 'test_main-cache')
DB = os.path.join(ROOTDIR, 'test_main-history.db')
STATE = os.path.join(ROOTDIR, 'test_main-state')
RESULTS = os.path.join(ROOTDIR, 'test_main-results')


def clear_files():
    if os.path.exists(CACHE):
        shutil.rmtree(CACHE)
    if os.path.exists(DB):
        os.remove(DB)
    if os.path.exists(STATE):
        os.remove(STATE)
    if os.path.exists(RESULTS):
        shutil.rmtree(RESULTS)


@contextmanager
def application(keep: bool = False):
    from isimple import settings, save_settings

    if not keep:
        clear_files()

    try:
        with settings.cache.override({"dir": CACHE, "do_cache": False}), \
                settings.db.override({"path": DB, "cleanup_interval": 0}), \
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

        if not keep:
            clear_files()


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

            MESSAGE = 'test log stream'

            client.put(
                '/api/check_design_path',
                data=json.dumps({"design_path": MESSAGE})
            )
            client.put(
                '/api/check_design_path',
                data=json.dumps({"design_path": MESSAGE})
            )

            time.sleep(1)

            client.put('/api/stop_log')

            thread.join()
            self.assertEqual(
                2,
                thread._data.count(MESSAGE.encode('utf-8'))
            )


class MainAnalyzerTest(unittest.TestCase):
    """Test Main methods -- VideoAnalyzer interaction"""

    CONFIG = {
        "video_path": __VIDEO__,
        "design_path": __DESIGN__,
        "features": [''],
        "feature_parameters": [{}],
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

            # Results are cleared after analyzing  todo: assert that results are in database
            self.assertTrue(
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
    def test_analyzer_undo_redo(self):
        with application() as (server, client, settings):
            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                client.post(
                    f'/api/{id}/call/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for ROI in self.ROI_SEQUENCE[::-1]:
                self.assertEqual(
                    ROI,
                    server._roots[id].config.transform.roi.to_dict()
                )
                client.post(f'/api/{id}/call/undo_config')

            for ROI in self.ROI_SEQUENCE:
                client.post(f'/api/{id}/call/redo_config')
                self.assertEqual(
                    ROI,
                    server._roots[id].config.transform.roi.to_dict()
                )

    def test_analyzer_undo_redo_context(self):
        with application() as (server, client, settings):
            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                # Changes to 'transform'
                client.post(
                    f'/api/{id}/call/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for CLICK in self.TRUE_HITS:
                # Changes to 'masks'
                client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps({'relative_x': CLICK[0], 'relative_y': CLICK[1]})
                )

            config_buffer = []
            config_buffer.append(server._roots[id].config.to_dict())

            # Undoing without a context -> everything changes
            client.post(f'/api/{id}/call/undo_config')
            config_buffer.append(server._roots[id].config.to_dict())

            self.assertEqual(  # 'transform' was not changed in the last set_config
                config_buffer[0]['transform'], config_buffer[1]['transform']
            )
            self.assertNotEqual(
                config_buffer[0]['masks'], config_buffer[1]['masks']
            )

            # Undoing with a context -> only the context changes
            client.post(f'/api/{id}/call/undo_config', data=json.dumps({'context': 'transform'}))
            config_buffer.append(server._roots[id].config.to_dict())

            self.assertNotEqual(  # 'transform' since it was set as the context, even though it was not changed in the previous config
                config_buffer[1]['transform'], config_buffer[2]['transform']
            )
            self.assertEqual(  # 'masks' doesn't change since the context is 'transform'
                config_buffer[1]['masks'], config_buffer[2]['masks']
            )

            # Undoing with a context -> only the context changes
            client.post(f'/api/{id}/call/undo_config', data=json.dumps({'context': 'transform'}))
            config_buffer.append(server._roots[id].config.to_dict())

            self.assertNotEqual(  # 'transform' since it was set as the context, even though it was not changed in the previous config
                config_buffer[2]['transform'], config_buffer[3]['transform']
            )
            self.assertEqual(  # 'masks' doesn't change since the context is 'transform'
                config_buffer[2]['masks'], config_buffer[3]['masks']
            )

            # Undoing with a context -> only the context changes
            # todo: takes two calls to undo_config to register, not sure why.
            client.post(f'/api/{id}/call/undo_config', data=json.dumps({'context': 'masks'}))
            client.post(f'/api/{id}/call/undo_config', data=json.dumps({'context': 'masks'}))
            config_buffer.append(server._roots[id].config.to_dict())

            self.assertEqual(  # 'transform' doesn't change since the context is 'masks
                config_buffer[3]['transform'], config_buffer[4]['transform']
            )
            self.assertNotEqual(  # 'masks' gets undone
                config_buffer[3]['masks'], config_buffer[4]['masks']
            )

            # Redoing with a context -> only the context changes
            client.post(f'/api/{id}/call/redo_config', data=json.dumps({'context': 'masks'}))
            config_buffer.append(server._roots[id].config.to_dict())

            self.assertEqual(  # 'transform' doesn't change since the context is 'masks'
                config_buffer[4]['transform'], config_buffer[5]['transform']
            )
            self.assertNotEqual(  # 'masks' gets redone
                config_buffer[4]['masks'], config_buffer[5]['masks']
            )

    def test_analyzer_undo_redo_invalid_context(self):
        with application() as (server, client, settings):
            id = json.loads(client.post('/api/init').data)

            self.assertRaises(
                ValueError,
                client.post,
                f'/api/{id}/call/undo_config',
                data=json.dumps({'context': 'illegal'})
            )
            self.assertRaises(
                ValueError,
                client.post,
                f'/api/{id}/call/redo_config',
                data=json.dumps({'context': 'illegal'})
            )

    def test_clean_db(self):
        clear_files()

        with application(keep=True) as (server, client, settings):
            id = json.loads(client.post('/api/init').data)
            client.post(
                f'/api/{id}/call/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                # Changes to 'transform'
                client.post(
                    f'/api/{id}/call/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for CLICK in self.TRUE_HITS:
                # Changes to 'masks'
                client.post(
                    f'/api/{id}/call/set_filter_click',
                    data=json.dumps(
                        {'relative_x': CLICK[0], 'relative_y': CLICK[1]})
                )

            from isimple.db import ConfigModel

            with server._history.session() as s:
                n_config_t0 = len(list(s.query(ConfigModel)))

        with application(keep=True) as (server, client, settings):
            server._history.clean()

            with server._history.session() as s:
                n_config_t1 = len(list(s.query(ConfigModel)))

        try:
            self.assertLess(n_config_t1, n_config_t0)
        finally:
            clear_files()

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


class DbCheckTest(unittest.TestCase):
    def test_db_check(self):
        from isimple import settings, save_settings

        with settings.db.override({'path': DB}):
            clear_files()
            save_settings(settings)

            import sqlite3

            db = sqlite3.connect(settings.db.path)
            cursor = db.cursor()

            cursor.execute("""
            CREATE TABLE video_file (
                id INTEGER PRIMARY KEY,
                hash TEXT,
                path TEXT,
                used TIMESTAMP
            );
            """)  # A correct table

            cursor.execute("""
                CREATE TABLE design_file (
                    id INTEGER PRIMARY KEY,
                    path TEXT,
                    used TIMESTAMP
                );
            """)  # An incorrect table

            # Not enough tables -> invalid

            db.commit()
            db.close()

            # runs check_history() on import, replaces invalid db
            from isimple.main import db
            import glob

            # db is now valid
            self.assertTrue(db.History().check())

            # There should be a broken db
            broken = glob.glob(f"{settings.db.path}_broken_*")

            self.assertEqual(1, len(broken))

            # clean up
            os.remove(broken[0])
            clear_files()


if __name__ == '__main__':
    unittest.main()

