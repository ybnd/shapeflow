import {
  api
} from '../api'

import {startServer, killServer, checkIfListening} from "../shapeflow";
import {test, describe, beforeEach, afterEach} from "@jest/globals";

beforeEach(() => {
  startServer();
});

afterEach(() => {
  killServer();
});

function run(test) {
  expect(checkIfListening()).toBe(true);

  api.ping().then(ok => {
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
      api.quit().then(ok => {
        // console.log('quit callback');
        expect(ok).toBe(true);
        while(checkIfListening()) {}
        expect(checkIfListening()).toBe(false);
        api.ping().then(ok => {
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
      api.unload().then(ok => {
        // console.log('unload callback');
        expect(ok).toBe(true);
        // console.log('ping 2');
        api.ping().then(ok => {
          console.log('ping 2 callback');
          expect(ok).toBe(true)
          api.quit().then(ok => {
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

