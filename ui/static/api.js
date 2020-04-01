import axios from "axios";
import { httpAdapter } from "axios/lib/adapters/http";

let API = "/api/";
let DB = "/db/";

export function url_api(id, endpoint = "") {
  return API + `${id}/${endpoint}`;
}

// define roi state Enum
export const AnalyzerState = {
  UNKNOWN: 0,
  INCOMPLETE: 1,
  CAN_LAUNCH: 2,
  LAUNCHED: 3,
  CAN_RUN: 4,
  RUNNING: 5,
  DONE: 6,
  CANCELED: 7,
  ERROR: 8
};

export function ping() {
  axios.get(API + "ping"); //todo: some indicator that pings are not coming through?
}

export function unload() {
  // axios can't be called on page unload, use sendBeacon instead
  return navigator.sendBeacon(API + "unload");
}
export async function list() {
  return axios.get(API + "list").then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function init() {
  // initialize an Analyzer in the backend & return its id
  return axios.post(API + "init").then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_schemas(id) {
  return axios.get(url_api(id, "call/get_schemas")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function check_video_path(video_path) {
  return axios
    .put(API + "check_video_path", { video_path: video_path })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function check_design_path(design_path) {
  return axios
    .put(API + "check_design_path", { design_path: design_path })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function get_config(id) {
  return axios.get(url_api(id, "call/get_config")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_state(id) {
  return axios.get(url_api(id, "get_state")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_relative_roi(id) {
  return axios.get(url_api(id, "call/get_relative_roi")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function set_config(id, config) {
  return axios
    .post(url_api(id, "call/set_config"), { config: config })
    .then(response => {
      if (response.status === 200) {
        return get_config(id).then(config => {
          // todo: backend set_config should return config
          return config;
        });
      }
    });
}

export async function launch(id) {
  return axios.get(url_api(id, "call/can_launch")).then(response => {
    if (response.status === 200) {
      return axios.post(url_api(id, "launch")).then(response => {
        if (response.status === 200) {
          return response.data;
        } else {
          return false;
        }
      });
    } else {
      return false;
    }
  });
}

export async function stream(id, endpoint) {
  return axios.get(url_api(id, `stream/${endpoint}`));
}

export async function seek(id, position) {
  axios
    .post(url_api(id, "call/seek"), { position: position })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      } else {
        return null;
      }
    });
}

export async function get_seek_position(id) {
  axios.get(url_api(id, "call/get_seek_position")).then(response => {
    if (response.status === 200) {
      return response.data;
    } else {
      return null;
    }
  });
}

export async function estimate_transform(id, roi) {
  return axios.post(url_api(id, "call/estimate_transform"), { roi: roi });
}

export async function set_filter(id, relative_coordinate) {
  return axios.post(url_api(id, "call/set_filter_click"), {
    relative_x: relative_coordinate.x,
    relative_y: relative_coordinate.y
  });
}

export async function analyze(id) {
  return axios.put(url_api(id, "call/analyze")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}

export function get_log() {
  var xhr = new XMLHttpRequest();
  xhr.open("GET", API + "get_log");
  xhr.send();

  return xhr;
}
