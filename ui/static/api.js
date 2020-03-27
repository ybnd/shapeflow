import axios from "axios";

let BACKEND_ROOT = ""; // todo: something something .env   https://stackoverflow.com/questions/49257650/
//       but also need to use CORS...

let API = BACKEND_ROOT + "/api/";
let DB = BACKEND_ROOT + "/db/";

export function url_api(id, endpoint) {
  return API + `${id}/${endpoint}`;
}
export function url_db(id, endpoint = "") {
  return DB + `${id}/${endpoint}`;
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
  console.log("Sending call/can_launch");
  return axios.get(url_api(id, "call/can_launch")).then(response => {
    console.log("call/can_launch got response");
    console.log(response);
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
  axios.get(url_api(id, "call/seek"), position).then(response => {
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

export function set_filter(id, coordinate) {
  // todo: check url
  // todo: provide coordinate ~ full frame, it's the backend's responsibility to resolve to the corresponding mask & color
  axios.post(url_path(id, "call/set_filter"), coordinate);
}

export function analyze(id) {
  return axios.put(url_api(id, "call/analyze")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}