// import axios from 'axios';
// jest.mock('axios');

const api = require('../api');

import {startServer, killServer} from "../shapeflow";
import {test} from "@jest/globals";


const SKIP = [api.axios, api.api, api.return_data, api.return_success, api.unload, api.events, api.get_log];
var MAP = undefined;

beforeAll(done => {
  startServer();

  function _map(map) {
    MAP = map;
    killServer();
    done();
  }

  api.map().then(_map).catch(() => {
    api.map().then(_map)
  });
})

test('validate map', () => {
  for (const rule in MAP) {
    expect(rule.slice(0,5)).toBe('/api/');
    expect(MAP[rule]).toContain('OPTIONS');
  }
});

describe('validate URLs', () => {
  for (const member in api) {
    if (api.hasOwnProperty(member) && typeof api[member] === "function" && !SKIP.includes(api[member])) {
      test(member, () => {
        var calls = {};

        // intercept axios requests & remember HTTP methods
        api.axios.get = jest.fn((url) => {
          calls = {...calls, [url]: 'GET'};
          return new Promise();
        })
        api.axios.put = jest.fn((url) => {
          calls = {...calls, [url]: 'PUT'};
          return new Promise();
        })
        api.axios.post = jest.fn((url) => {
          calls = {...calls, [url]: 'POST'};
          return new Promise();
        })

        // call method
        api[member]('<id>', '<endpoint>');
        // if URL depends on <id>, it's the first argument -> URL gets resolved to Flask rule
        // if URL dependes on <endpoint>, it's the second arguments
        // in other cases, these arguments are either unused or used as data and consequently _not_ tested here.

        // validate HTTP methods for each URL
        for (const url in calls) {
          const method = calls[url];
          var allowed;
          if (MAP[url] === undefined) {
            if (url.match(/^\/api\/<id>\/call\//g)) {
              // resolve specific endpoint URL to rule
              allowed = MAP['/api/<id>/call/<endpoint>'];
            } else if (url.match(/^\/api\/db\//g)) {
              // resolve specific endpoint URL to rule
              allowed = MAP['/api/db/<endpoint>'];
            }
          } else {
            allowed = MAP[url];
          }
          expect(allowed).toContain(method);
        }
      });
    }
  }
});


