import axios from "axios";
import { resolvePath } from "vue-router/src/util/path";

let BACKEND_ROOT = "http://localhost:7951"; // todo: something something .env   https://stackoverflow.com/questions/49257650/
//       but also need to use CORS...

let API = BACKEND_ROOT + "/api/";
let DB = BACKEND_ROOT + "/db/";
let STREAM = BACKEND_ROOT + "/stream/";

export function url_api(id, endpoint) {
  return API + `${id}/${endpoint}`;
}
export function url_db(id, endpoint = "") {
  return DB + `${id}/${endpoint}`;
}
export function url_stream(id, endpoint) {
  return STREAM + `${id}/${endpoint}`;
}

// define analyzer state Enum
export const analyzer_state = {
  unset: 0,
  INCOMPLETE: 1,
  LAUNCHED: 2,
  RUNNING: 3,
  CANCELED: 4,
  ERROR: 5
};

export function ping() {
  axios.get(API + "ping"); //todo: some indicator that pings are not coming through?
}

export function unload() {
  // axios can't be called on page unload, use sendBeacon instead
  return navigator.sendBeacon(API + "unload");
}
export function list() {
  axios.get(API + "list");
}

export function init() {
  // initialize an Analyzer in the backend & return its id
  axios.post(API + "init").then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export function get_schemas(id) {
  axios.get(url_api(id, "schemas")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export function get_config(id) {
  axios.get(url_api(id, "get_config")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export function set_config(id, config) {
  axios.post(url_api(id, "set_config"), config).then(response => {
    if (response.status === 200) {
      get_config(id).then(config => {
        return config;
      });
    }
  });
}

export function launch(id) {
  axios.get(url_api(id, "can_launch")).then(response => {
    if (response.status === 200) {
      axios.put(url_api(id, "launch")).then(response => {
        if (response.status === 200) {
          return true;
        }
      });
    }
  });
}

export function estimate_transform(id, roi) {
  // todo: check url
  axios.put(url_api(id, "call/estimate_transform"), roi);
}

export function set_filter(id, coordinate) {
  // todo: check url
  // provide coordinate ~ full frame, it's the backend's responsibility to resolve to the corresponding mask & color
  axios.put(url_path(id, "call/set_filter"), coordinate);
}

export function analyze(id) {
  axios.put(url_api(id, "call/analyze")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}
