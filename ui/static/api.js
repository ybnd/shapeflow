import axios from "axios";

let API = "/api/";

export function url() {
  return API + Array.from(arguments).join("/");
}

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
  // todo: deprecated, just ping with list()
  axios.get(url("ping"));
}

export function unload() {
  // axios can't be called on page unload, use sendBeacon instead
  return navigator.sendBeacon(url("unload"));
}

export async function settings_schema() {
  return axios.get(url("settings_schema")).then(response => {
    if (response.status === 200) {
      return response.data; // todo: this pattern is QUITE common
    }
  });
}

export async function get_settings() {
  return axios.get(url("get_settings")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function set_settings(settings) {
  return axios
    .post(url("set_settings"), { settings: settings })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function list() {
  return axios.get(url("list")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function init() {
  // initialize an Analyzer in the backend & return its id
  return axios.post(url("init")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function remove(id) {
  return axios.post(url(id, "remove")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function cancel(id) {
  return axios.post(url(id, "cancel")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_schemas(id) {
  return axios.get(url(id, "call/get_schemas")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_options(for_type) {
  return axios.get(url("options", for_type)).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function select_video_path() {
  return axios.get(url("select_video_path")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function select_design_path() {
  return axios.get(url("select_design_path")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function check_video_path(video_path) {
  return axios
    .put(url("check_video_path"), { video_path: video_path })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function check_design_path(design_path) {
  return axios
    .put(url("check_design_path"), { design_path: design_path })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function get_config(id) {
  return axios.get(url(id, "call/get_config")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_state(id) {
  return axios.get(url(id, "get_state")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_status(id) {
  return axios.get(url(id, "call/status")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function get_relative_roi(id) {
  return axios.get(url(id, "call/get_relative_roi")).then(response => {
    if (response.status === 200) {
      return response.data;
    }
  });
}

export async function set_config(id, config) {
  return axios
    .post(url(id, "call/set_config"), { config: config })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      }
    });
}

export async function launch(id) {
  return axios.get(url(id, "call/can_launch")).then(response => {
    if (response.status === 200) {
      return axios.post(url(id, "launch")).then(response => {
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

export async function seek(id, position) {
  return axios
    .post(url(id, "call/seek"), { position: position })
    .then(response => {
      if (response.status === 200) {
        return response.data;
      } else {
        return null;
      }
    });
}

export async function get_seek_position(id) {
  return axios.get(url(id, "call/get_seek_position")).then(response => {
    if (response.status === 200) {
      return response.data;
    } else {
      return null;
    }
  });
}

export async function estimate_transform(id, roi) {
  return axios
    .post(url(id, "call/estimate_transform"), { roi: roi })
    .then(response => {
      if (response.status === 200) {
        return true;
      }
    });
}

export async function clear_roi(id) {
  return axios.post(url(id, "call/clear_roi")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}

export async function undo_roi(id) {
  return axios.put(url(id, "call/undo_roi")).then(response => {
    if (response.status === 200) {
      return response.data;
    } else {
      return null;
    }
  });
}

export async function redo_roi(id) {
  return axios.put(url(id, "call/redo_roi")).then(response => {
    if (response.status === 200) {
      return response.data;
    } else {
      return null;
    }
  });
}

export async function set_filter(id, relative_coordinate) {
  return axios
    .post(url(id, "call/set_filter_click"), {
      relative_x: relative_coordinate.x,
      relative_y: relative_coordinate.y
    })
    .then(response => {
      if (response.status === 200) {
        if ("message" in response.data) {
          return response.data.message;
        }
      }
    });
}

export async function commit(id) {
  return axios.post(url(id, "call/commit")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}

export async function analyze(id) {
  return axios.put(url(id, "call/analyze")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}

export function get_log() {
  // todo: add link to where this was copied from!
  var xhr = new XMLHttpRequest();
  xhr.open("GET", API + "get_log");
  xhr.send();

  return xhr;
}

export async function stop_log() {
  return axios.put(url("/stop_log")).then(response => {
    if (response.status === 200) {
      return true;
    }
  });
}

export function stream(id, endpoint, callback) {
  console.log(`registering EventSource for ${id}/${endpoint}`);

  let evl = new EventSource(url(id, endpoint));
  evl.onmessage = callback;

  console.log(evl);
  return evl;
}
