import os
import shutil
import unittest
from unittest.mock import MagicMock
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
if os.getcwd() == '/home/travis/build/ybnd/shapeflow':
    __VIDEO__ = 'test/' + __VIDEO__
    __DESIGN__ = 'test/' + __DESIGN__

from shapeflow import ROOTDIR


CACHE = os.path.join(ROOTDIR, 'test_server-cache')
DB = os.path.join(ROOTDIR, 'test_server-history.db')
STATE = os.path.join(ROOTDIR, 'test_server-state')
RESULTS = os.path.join(ROOTDIR, 'test_server-results')


def clear_files():
    if os.path.isdir(CACHE):
        shutil.rmtree(CACHE)
    if os.path.isfile(DB):
        os.remove(DB)
    if os.path.isfile(STATE):
        os.remove(STATE)
    if os.path.isdir(RESULTS):
        shutil.rmtree(RESULTS)


@contextmanager
def application(keep: bool = False):
    from shapeflow import settings, save_settings

    if not keep:
        clear_files()

    try:
        with settings.cache.override({"dir": CACHE, "do_cache": False, "reset_on_error": True}), \
                settings.db.override({"path": DB, "cleanup_interval": 0}), \
                settings.app.override({"state_path": STATE, "save_result_auto": 'in result directory', "result_dir": RESULTS, "cancel_on_q_stop": False}), \
                settings.log.override({'lvl_console': 'debug', 'lvl_file': 'debug'}):
            save_settings()

            # import from shapeflow.server here -> current settings are respected
            import shapeflow.server
            import shapeflow.db
            import shapeflow.main

            server = shapeflow.server.ShapeflowServer()
            server._raise_call_exceptions = True
            server._history = shapeflow.db.History(settings.db.path)
            server._app.testing = True
            client = server._app.test_client()

            api = shapeflow.main.load(server)
            analyzers = api.va._instance.__analyzers__
            history = api.va._instance._history

            yield server, analyzers, history, client, settings
    finally:
        save_settings()

        # Explicitly remove any leftover analyzers
        app_state = json.loads(client.get('/api/va/state').data)
        for id in app_state['ids']:
            client.post(f'/api/va/close?id={id}')

        del server
        del settings

        if not keep:
            clear_files()


class ServerTest(unittest.TestCase):
    """Test global methods """
    def test_file_checks(self):
        with application() as (server, analyzers, history, client, settings):
            # Check real files
            self.assertEqual(
                True,
                json.loads(
                    client.put(
                        '/api/fs/check_design',
                        data=json.dumps({"path": __DESIGN__})
                    ).data
                )
            )
            self.assertEqual(
                True,
                json.loads(
                    client.put(
                        '/api/fs/check_video',
                        data=json.dumps({"path": __VIDEO__})
                    ).data
                )
            )

            # Check wrong real files
            self.assertEqual(
                True,  # OnionSVG.check_svg() checks if directory contains <file>.svg if extension doesn't match
                json.loads(
                    client.put(
                        '/api/fs/check_design',
                        data=json.dumps({"path": __VIDEO__})
                    ).data
                )
            )
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/fs/check_video',
                        data=json.dumps({"path": __DESIGN__})
                    ).data
                )
            )

            # Check fake files
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/fs/check_design',
                        data=json.dumps({"path": "test1.svg"})
                    ).data
                )
            )
            self.assertEqual(
                False,
                json.loads(
                    client.put(
                        '/api/fs/check_video',
                        data=json.dumps({"path": "test2.mp4"})
                    ).data
                )
            )

    def test_log_stream(self):  # todo: this one passes by itself but fails otherwise
        with application() as (server, analyzers, history, client, settings):
            class LogStreamThread(Thread):
                def run(self):
                    self._data = client.get('/api/log').data

            thread = LogStreamThread()
            thread.start()

            MESSAGE = 'test log stream'

            client.put(
                '/api/fs/check_design',
                data=json.dumps({"path": MESSAGE})
            )
            client.put(
                '/api/fs/check_design',
                data=json.dumps({"path": MESSAGE})
            )

            time.sleep(2)  # wait a bit longer to make sure lines get pushed

            client.put('/api/stop_log')

            thread.join()
            self.assertEqual(
                2,
                thread._data.count(MESSAGE.encode('utf-8'))
            )


class ServerAnalyzerTest(unittest.TestCase):
    """Test VideoAnalyzer methods"""

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
        with application() as (server, analyzers, history, client, settings):
            r = client.post('/api/va/init')
            self.assertEqual(200, r.status_code)

            id = json.loads(r.data)
            self.assertNotEqual('', id)

            self.assertIn(id, analyzers)
            self.assertFalse(
                json.loads(client.get(f'/api/va/{id}/can_launch').data)
            )

            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.get(f'/api/va/{id}/can_launch').data)
            )
            self.assertTrue(
                json.loads(client.post(f'/api/va/{id}/launch').data)
            )
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": {"transform": {"roi": None}}})
            )

            # Can't analyze yet since transform.roi is not set
            self.assertFalse(json.loads(client.post(f'/api/va/{id}/analyze').data))

            client.post(
                f'/api/va/{id}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            self.assertEqual(
                self.ROI,
                analyzers[id].transform.config.roi
            )

            # Ignore all masks
            Nmasks = len(analyzers[id].config.masks)
            analyzers[id].set_config(
                    {'masks': [{'skip': True}] * Nmasks}
                )

            self.assertTrue(json.loads(client.post(f'/api/va/{id}/analyze').data))

            # Results are cleared after analyzing  todo: assert that results are in database
            self.assertTrue(
                analyzers[id].results[
                    analyzers[id].config.features[0]].isna().all().all()
            )

            client.post(f'/api/va/close?id={id}')
            self.assertNotIn(id, analyzers)

    def test_analyzer_roi_flip(self):
        with application() as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id}/launch')

            client.post(
                f'/api/va/{id}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({ "config": {"transform":
                    {"flip": {"horizontal": True, "vertical": True}}}})
            )

            self.assertEqual(
                {"horizontal": True, "vertical": True},
                analyzers[id].transform.config.flip.to_dict()
            )

            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": {"transform":
                    {"flip": {"horizontal": False}}}})
            )

            # Previous value of transform.flip.vertical should still be remembered
            self.assertEqual(
                {"horizontal": False, "vertical": True},
                analyzers[id].transform.config.flip.to_dict()
            )

    def test_analyzer_filter_click(self):
        with application() as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id}/launch')
            client.post(
                f'/api/va/{id}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            for click in self.MISSES:
                og_masks = analyzers[id].config.to_dict()['masks']
                r = client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertEqual(og_masks, analyzers[id].config.to_dict()['masks'])  # todo: no response anymore ~06024b46

            for click in self.FAKE_HITS:
                og_masks = analyzers[id].config.to_dict()['masks']
                r = client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertEqual(og_masks, analyzers[id].config.to_dict()['masks'])  # todo: no response anymore ~06024b46

            for click in self.TRUE_HITS:
                og_masks = analyzers[id].config.to_dict()['masks']
                r = client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps({'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertNotEqual(og_masks, analyzers[id].config.to_dict()['masks'])  # todo: no response anymore ~06024b46

            for click in self.DOUBLE_HITS:
                og_masks = analyzers[id].config.to_dict()['masks']
                r = client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps(
                        {'relative_x': click[0], 'relative_y': click[1]})
                )
                self.assertEqual(og_masks, analyzers[id].config.to_dict()['masks'])  # todo: no response anymore ~06024b46

    def test_analyzer_history(self):
        with application() as (server, analyzers, history, client, settings):
            id1 = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id1}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id1}/launch')
            client.post(
                f'/api/va/{id1}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            client.post(f'/api/va/close?id={id1}')

            id2 = json.loads(client.post('/api/va/init').data)

            self.assertNotEqual(id1, id2)

            client.post(
                f'/api/va/{id2}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.get(f'/api/va/{id2}/can_launch').data)
            )
            self.assertTrue(
                json.loads(client.post(f'/api/va/{id2}/launch').data)
            )
            self.assertEqual(
                self.ROI,
                json.loads(
                    client.get(f'/api/va/{id2}/get_config'
                ).data)['transform']['roi']
            )

    def test_analyzer_undo_redo(self):
        with application() as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                client.post(
                    f'/api/va/{id}/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for ROI in self.ROI_SEQUENCE[::-1]:
                self.assertEqual(
                    ROI,
                    analyzers[id].config.transform.roi.to_dict()
                )
                client.post(f'/api/va/{id}/undo_config')

            for ROI in self.ROI_SEQUENCE:
                client.post(f'/api/va/{id}/redo_config')
                self.assertEqual(
                    ROI,
                    analyzers[id].config.transform.roi.to_dict()
                )

    def test_analyzer_undo_redo_context(self):
        with application() as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                # Changes to 'transform'
                client.post(
                    f'/api/va/{id}/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for CLICK in self.TRUE_HITS:
                # Changes to 'masks'
                client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps({'relative_x': CLICK[0], 'relative_y': CLICK[1]})
                )

            config_buffer = []
            config_buffer.append(analyzers[id].config.to_dict())

            # Undoing without a context -> everything changes
            client.post(f'/api/va/{id}/undo_config')
            config_buffer.append(analyzers[id].config.to_dict())

            self.assertEqual(  # 'transform' was not changed in the last set_config
                config_buffer[0]['transform'], config_buffer[1]['transform']
            )
            self.assertNotEqual(
                config_buffer[0]['masks'], config_buffer[1]['masks']
            )

            # Undoing with a context -> only the context changes
            client.post(f'/api/va/{id}/undo_config', data=json.dumps({'context': 'transform'}))
            config_buffer.append(analyzers[id].config.to_dict())

            self.assertNotEqual(  # 'transform' since it was set as the context, even though it was not changed in the previous config
                config_buffer[1]['transform'], config_buffer[2]['transform']
            )
            self.assertEqual(  # 'masks' doesn't change since the context is 'transform'
                config_buffer[1]['masks'], config_buffer[2]['masks']
            )

            # Undoing with a context -> only the context changes
            client.post(f'/api/va/{id}/undo_config', data=json.dumps({'context': 'transform'}))
            config_buffer.append(analyzers[id].config.to_dict())

            self.assertNotEqual(  # 'transform' since it was set as the context, even though it was not changed in the previous config
                config_buffer[2]['transform'], config_buffer[3]['transform']
            )
            self.assertEqual(  # 'masks' doesn't change since the context is 'transform'
                config_buffer[2]['masks'], config_buffer[3]['masks']
            )

            # Undoing with a context -> only the context changes
            # todo: takes two calls to undo_config to register, not sure why.
            client.post(f'/api/va/{id}/undo_config', data=json.dumps({'context': 'masks'}))
            client.post(f'/api/va/{id}/undo_config', data=json.dumps({'context': 'masks'}))
            config_buffer.append(analyzers[id].config.to_dict())

            self.assertEqual(  # 'transform' doesn't change since the context is 'masks
                config_buffer[3]['transform'], config_buffer[4]['transform']
            )
            self.assertNotEqual(  # 'masks' gets undone
                config_buffer[3]['masks'], config_buffer[4]['masks']
            )

            # Redoing with a context -> only the context changes
            client.post(f'/api/va/{id}/redo_config', data=json.dumps({'context': 'masks'}))
            config_buffer.append(analyzers[id].config.to_dict())

            self.assertEqual(  # 'transform' doesn't change since the context is 'masks'
                config_buffer[4]['transform'], config_buffer[5]['transform']
            )
            self.assertNotEqual(  # 'masks' gets redone
                config_buffer[4]['masks'], config_buffer[5]['masks']
            )

    def test_analyzer_undo_redo_invalid_context(self):
        with application() as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)

            self.assertRaises(
                ValueError,
                client.post,
                f'/api/va/{id}/undo_config',
                data=json.dumps({'context': 'illegal'})
            )
            self.assertRaises(
                ValueError,
                client.post,
                f'/api/va/{id}/redo_config',
                data=json.dumps({'context': 'illegal'})
            )

    def test_clean_db(self):
        clear_files()

        with application(keep=True) as (server, analyzers, history, client, settings):
            id = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id}/launch')

            for ROI in self.ROI_SEQUENCE:
                # Changes to 'transform'
                client.post(
                    f'/api/va/{id}/set_config',
                    data=json.dumps({"config": {"transform": {"roi": ROI}}})
                )

            for CLICK in self.TRUE_HITS:
                # Changes to 'masks'
                client.post(
                    f'/api/va/{id}/set_filter_click',
                    data=json.dumps(
                        {'relative_x': CLICK[0], 'relative_y': CLICK[1]})
                )

            from shapeflow.db import ConfigModel

            with history.session() as s:
                n_config_t0 = len(list(s.query(ConfigModel)))

        with application(keep=True) as (server, analyzers, history, client, settings):
            history.clean()

            with history.session() as s:
                n_config_t1 = len(list(s.query(ConfigModel)))

        try:
            self.assertLess(n_config_t1, n_config_t0)  # todo: this fails now, what changed?
        finally:
            clear_files()

    @unittest.skip("doesn't work after 06024b46")  # todo: have to bypass CAN_FILTER by setting up all masks
    def test_analyzers_queue_ops(self):
        with application() as (server, analyzers, history, client, settings):
            id1 = json.loads(client.post('/api/va/init').data)
            client.post(
                f'/api/va/{id1}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )
            client.post(f'/api/va/{id1}/launch')
            client.post(
                f'/api/va/{id1}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            id2 = json.loads(client.post('/api/va/init').data)

            client.post(
                f'/api/va/{id2}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.post(f'/api/va/{id2}/launch').data)
            )
            client.post(
                f'/api/va/{id2}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            id3 = json.loads(client.post('/api/va/init').data)

            client.post(
                f'/api/va/{id3}/set_config',
                data=json.dumps({"config": self.CONFIG})
            )

            self.assertTrue(
                json.loads(client.post(f'/api/va/{id3}/launch').data)
            )
            client.post(
                f'/api/va/{id3}/estimate_transform',
                data=json.dumps({"roi": self.ROI})
            )

            app_state = json.loads(client.get('/api/va/state').data)
            self.assertEqual(
                0,  # QueueState.STOPPED
                app_state['q_state']
            )

            # Start queue in separate thread (don't block until done)
            thread = Thread(
                target=client.post,
                args=['/api/va/start'],
                kwargs={'data': json.dumps({'queue': [id1, id2, id3]})}
            )
            thread.start()

            # Stop queue while not done yet
            client.post('/api/va/stop')
            thread.join()

            app_state = json.loads(client.get('/api/va/state').data)
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
            client.post('/api/va/start', data=json.dumps({'queue': [id3, id2, id1]}))

            app_state = json.loads(client.get('/api/va/state').data)
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
        from shapeflow import settings, save_settings

        with settings.db.override({'path': DB}):
            clear_files()
            save_settings()

            import sqlite3

            c = sqlite3.connect(settings.db.path)
            cursor = c.cursor()

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

            c.commit()
            c.close()

            # run check_history(), replaces invalid db
            from shapeflow.main import _Database, History
            import glob

            server = MagicMock()
            server._eventstreamer = None

            db = _Database(server)
            db.check_history()

            # db is now valid
            self.assertTrue(History().check())

            # There should be a broken db
            broken = glob.glob(f"{settings.db.path}_broken_*")

            self.assertEqual(1, len(broken))

            # clean up
            os.remove(broken[0])
            clear_files()


if __name__ == '__main__':
    unittest.main()

