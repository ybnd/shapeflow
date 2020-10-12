import {
  quit, ping, unload, restart, settings_schema, get_settings, set_settings, open_root,
  select_video_path, select_design_path, check_video_path, check_design_path
} from '../api'

import {startServer, killServer, checkIfListening} from "../shapeflow";
import {test, describe, beforeEach, afterEach} from "@jest/globals";

beforeEach(startServer)
afterEach(killServer)

describe('server interactions', () => {
  test('ping & quit & ping', done => {
    try {
      expect(checkIfListening()).toBe(true);
      // console.log('ping 1');

      function run(ok) {
        // console.log('ping 1 callback');
        expect(ok).toBe(true);
        // console.log('quit');
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
        })
      }

      ping().then(ok => {
        run(ok);
      }).catch(error => {
        // server should be up, just retry
        ping().then(ok => {
          run(ok)
        })
      })
    } catch (e) {
      done(e);
    }
  })

  test('ping & unload & ping', done => {
    try {
      expect(checkIfListening()).toBe(true);
      // console.log('ping 1')

      function run(ok) {
        // console.log('ping 1 callback');
        expect(ok).toBe(true);
        // console.log('unload');
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
      }

      ping().then(ok => {
        run(ok);
      }).catch(error => {
        // server should be up, just retry
        ping().then(ok => {
          run(ok);
        });
      });
    } catch (e) {
      done(e);
    }
  })

  test('ping & restart & ping', done => {
    try {
      expect(checkIfListening()).toBe(true);
      // console.log('ping 1')

      function run(ok) {
        // console.log('ping 1 callback')
        expect(ok).toBe(true);
        // console.log('restart')
        restart().then(ok => {
          // console.log('restart callback')
          expect(ok).toBe(true);
        }).catch(e => {
          // console.warn('restart catch', e)
        });
        setTimeout(() => {
          // console.log('ping 2')
          ping().then(ok => {
            // console.log('ping 2 callback')
            expect(ok).toBe(true);
            quit().then(ok => {
              expect(ok).toBe(true);
              setTimeout(() => {
                done();
              }, 1000)
            });
          }, 2000)
        });
      }

      ping().then(ok => {  // todo: fails with "socket hang up" for unclear reasons
        run(ok);
      }).catch(error => {
        // server should be up, just retry
        ping().then(ok => {
          run(ok);
        });
      });
    } catch (e) {
      done(e);
    }
  })
})
