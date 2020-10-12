import {api_map} from '../api'

import {startServer, killServer, checkIfListening, waitSync} from "../shapeflow";
import {test, describe, beforeEach, afterEach} from "@jest/globals";


var MAP = undefined;

beforeAll(done => {
  startServer();

  function _map(map) {
    MAP = map;
    killServer();
    done();
  }

  api_map().then(_map).catch(() => {
    api_map().then(_map)
  });
})

test()
