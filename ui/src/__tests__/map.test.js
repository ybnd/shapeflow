import axios from 'axios';
import { api } from '../api';

import {retryOnce} from "../util";
import {startServer, killServer} from "../shapeflow";
import {test, describe} from "@jest/globals";


const SKIP = [
  api.events,         // uses EventSource instead of axios
  api.log,            // uses XMLHttpRequest instead of axios
  api.va.stream_stop  // special case; URL changes ~ ID / ENDPOINT
];
var MAP = undefined;

beforeAll(async () => {
  startServer();
  MAP = await retryOnce(api.map);
  killServer();
});

test('validate map', () => {
  for (const rule in MAP) {
    expect(rule.slice(0,5)).toBe('/api/');
    expect(MAP[rule]).toContain('OPTIONS');
  }
});

describe('validate URLs', () => {
  var calls;

  beforeEach(() => {
    calls = {};

    // intercept axios requests & remember HTTP methods
    axios.get = jest.fn((url) => {
      calls = {...calls, [url]: calls[url] !== undefined ? [...calls[url], 'GET'] : ['GET']};
      return Promise.resolve(undefined);
    })
    axios.put = jest.fn((url) => {
      calls = {...calls, [url]: calls[url] !== undefined ? [...calls[url], 'PUT'] : ['PUT']};
      return Promise.resolve(undefined);
    })
    axios.post = jest.fn((url) => {
      calls = {...calls, [url]: calls[url] !== undefined ? [...calls[url], 'POST'] : ['POST']};
      return Promise.resolve(undefined);
    })
  });

  function _for_every_method(obj, callback) {
    for (const member in obj) {  // todo: need to flatten :/
      if (obj.hasOwnProperty(member) && typeof obj[member] === "function" && !SKIP.includes(obj[member])) {
        callback(obj, member);
      }
    }
  }

  function _for_every_url_called(callback) {
    for (const url in calls) {
      if (calls.hasOwnProperty(url)) {
        callback(url);
      } else {
        console.log('oops')
      }
    }
  }

  describe("/api/", () => {
    _for_every_method(api, (obj, member) => {
      test(member, () => {
        // call method
        obj[member]();

        // validate HTTP methods for each URL called
        _for_every_url_called((url) => {
          expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
        })
      });
    });
  });

  describe("/api/fs", () => {
    _for_every_method(api.fs, (obj, member) => {
      test(member, () => {
        // call method
        obj[member]();

        // validate HTTP methods for each URL called
        _for_every_url_called((url) => {
          expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
        })
      });
    });
  });

  describe("/api/db/", () => {
    _for_every_method(api.db, (obj, member) => {
      test(member, () => {
        // call method
        obj[member]();

        // validate HTTP methods for each URL called
        _for_every_url_called((url) => {
          expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
        })
      });
    });
  });

  describe("/api/cache/", () => {
    _for_every_method(api.cache, (obj, member) => {
      test(member, () => {
        // call method
        obj[member]();

        // validate HTTP methods for each URL called
        _for_every_url_called((url) => {
          expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
        })
      });
    });
  });

  describe("/api/va/", () => {
    _for_every_method(api.va, (obj, member) => {
      test(member, () => {
        // call method
        obj[member]();

        // validate HTTP methods for each URL called
        _for_every_url_called((url) => {
          expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
        })
      });
    });
  });

  describe("/api/va/__id__/", () => {
    const ID = "__id__";

    _for_every_method(api.va.__id__, (obj, member) => {
      test(member, (done) => {
        obj[member](ID)
          .catch(() => {
            // noop
          })
          .finally(() => {
            // validate HTTP methods for each URL called
            _for_every_url_called((url) => {
              expect(MAP[url]).toEqual(expect.arrayContaining(calls[url]))
            })
            done();
          })
      });
    });
  });
});


