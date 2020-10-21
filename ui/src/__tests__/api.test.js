import {
  quit, ping, unload, restart, settings_schema, get_settings, set_settings, open_root,
  select_video_path, select_design_path, check_video_path, check_design_path
} from '../api'

import {startServer, killServer, checkIfListening, waitSync} from "../shapeflow";
import {test, describe, beforeEach, afterEach} from "@jest/globals";

beforeEach(startServer)
afterEach(killServer)

function run(test) {
  expect(checkIfListening()).toBe(true);

  ping().then(ok => {
    expect(ok).toBe(true);
    try {
      test();
    } catch(e) {
      run(test);
    }
  }).catch(() => {
    run(test);
  })
}

test('quit', done => {
  try {
    run(() => {
      quit().then(ok => {
        // console.log('quit callback');
        expect(ok).toBe(true);
        while(checkIfListening()) {}
        expect(checkIfListening()).toBe(false);
        ping().then(ok => {
          console.log('ping 2 callback');
          expect(ok).toBe(false);
          done();
        });
      });
    });
  } catch (e) {
    done(e);
  }
});

test('unload', done => {
  try {
    run(() => {
      unload().then(response => {
        // console.log('unload callback');
        expect(response.status).toBe(200);
        // console.log('ping 2');
        ping().then(ok => {
          console.log('ping 2 callback');
          expect(ok).toBe(true)
          quit().then(ok => {
            expect(ok).toBe(true);
            while(checkIfListening()) {}
            expect(checkIfListening()).toBe(false);
            done();
          })
        });
      });
    });
  } catch (e) {
    done(e);
  }
});

