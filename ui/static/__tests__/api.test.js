import {
  quit, ping, unload, restart, settings_schema, get_settings, set_settings, open_root,
  select_video_path, select_design_path, check_video_path, check_design_path
} from '../api'

import {startServer, killServer, checkIfListening} from "../shapeflow";
import {exec, execSync, spawn, spawnSync} from 'child_process';
import {EventEmitter} from 'events';
import {test, describe, beforeEach, afterEach, beforeAll, afterAll} from "@jest/globals";
import {Validator, validate} from "jsonschema";


beforeAll(killServer)
beforeEach(startServer)
afterEach(killServer)
afterAll(killServer)


describe('server interactions', () => {
  test('ping & quit & ping', done => {
    try {
      expect(checkIfListening()).toBe(true)
      // console.log('ping 1');
      expect()
      ping().then(ok => {
        // console.log('ping 1 callback');
        expect(ok).toBe(true);
        // console.log('quit');
        quit().then(ok => {
          // console.log('quit callback');
          expect(ok).toBe(true);
          setTimeout(() => {
            // console.log('ping 2');
            expect(checkIfListening()).toBe(false)
            ping().then(ok => {
              // console.log('ping 2 callback');
              expect(ok).toBe(false);
              done();
            })
          }, 1000)
        })
      })
    } catch (e) {
      done(e);
    }
  })

  test('ping & unload & ping', done => {
    try {
      // console.log('ping 1')
      ping().then(ok => {
        expect(checkIfListening()).toBe(true)
        // console.log('ping 1 callback');
        expect(ok).toBe(true);
        // console.log('unload');
        unload().then(response => {
          // console.log('unload callback');
          expect(response.status).toBe(200);
          // console.log('ping 2');
          ping().then(ok => {
            // console.log('ping 2 callback');
            expect(ok).toBe(true)
            quit().then(ok => {
              expect(ok).toBe(true);
              setTimeout(() => {
                expect(checkIfListening()).toBe(false)
                done();
              }, 1000)
            });
          })

        })
      })
    } catch (e) {
      done(e);
    }
  })

  test('ping & restart & ping', done => {
    try {
      expect(checkIfListening()).toBe(true)
      // console.log('ping 1')
      ping().then(ok => {
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
                expect(checkIfListening()).toBe(false)
                done();
              }, 1000)
            });
          }, 2000)
        })
      })
    } catch (e) {
      done(e);
    }
  })
})
