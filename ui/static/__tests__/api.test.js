import {
  quit, ping, unload, restart, settings_schema, get_settings, set_settings, open_root,
  select_video_path, select_design_path, check_video_path, check_design_path
} from '../api'

import {exec, execSync, spawn, spawnSync} from 'child_process';
import {EventEmitter} from 'events';
import {test, describe, beforeEach, afterEach, beforeAll, afterAll} from "@jest/globals";
import {Validator, validate} from "jsonschema";


var SERVER = undefined

async function _kill() {
  // console.log('stopping server')
  try {
    if (SERVER !== undefined) {
      execSync(`kill -9 ${SERVER.pid}`)
    }
    execSync('pkill -f "python3 shapeflow"')
    if (SERVER !== undefined) {
      execSync(`kill -9 ${SERVER.pid}`)
    }
  } catch(e) {
    // console.warn(e)
  }

  SERVER = undefined;
  const end = Date.now() + 1000;
  while (Date.now() < end) {}
}

beforeAll(_kill)
beforeEach(() => {
  // console.log('starting server...')
  SERVER = spawn(
    'python3', ['shapeflow.py', '--server'],
    {cwd: '..', shell: false, detached: false}
    )

  const end = Date.now() + 1000;
  while (Date.now() < end) {}
})

afterEach(_kill)
afterAll(_kill)

describe('server interactions', () => {
  test('ping & quit & ping', done => {
    try {
      // console.log('ping 1');
      ping().then(ok => {
        // console.log('ping 1 callback');
        expect(ok).toBe(true);
        // console.log('quit');
        quit().then(ok => {
          // console.log('quit callback');
          expect(ok).toBe(true);
          setTimeout(() => {
            // console.log('ping 2');
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
                done()
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
                done()
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
