import axios from "axios";


export function url() {
  return "/api/" + Array.from(arguments).join("/");
}

export const AnalyzerState = {
  UNKNOWN: 0,
  INCOMPLETE: 1,
  CAN_LAUNCH: 2,
  LAUNCHED: 3,
  CAN_FILTER: 4,
  CAN_ANALYZE: 5,
  ANALYZING: 6,
  DONE: 7,
  CANCELED: 8,
  ERROR: 9,
};

export const QueueState = {
  STOPPED: 0,
  RUNNING: 1,
  PAUSED: 2,
};

export const EVENT_CATEGORIES = ["status", "config", "notice", "close"];

export const NOTICE_TIMEOUT = 10000;
export const NOTICE_LIMIT = 8;

export const endpoints = {
  GET_INVERSE_OVERLAID_FRAME: "get_inverse_overlaid_frame",
  GET_STATE_FRAME: "get_state_frame",
  GET_FRAME: "get_frame",
  GET_OVERLAY_PNG: "get_overlay_png",
};

function return_data(response) {
  if (response.status === 200) {
    return response.data;
  }
}

function return_success(response) {
  return response.status === 200;
}


export const api = {
  async ping() {
    return axios
      .get(url("ping"))
      .then(return_success)
      .catch(() => {
        return false;
      });
  },
  async unload() {
    try {
      // axios can't be called on page unload, use sendBeacon instead
      return navigator.sendBeacon(url("unload"));
    } catch(e) {
      // use axios for unit tests
      console.warn(e);
      return axios
        .post(url('unload'))
        .then(return_success);
    }
  },
  async quit() {
    return axios
      .post(url("quit"))
      .then(return_success);
  },
  async restart() {
    return axios
      .post(url("restart"))
      .then(return_data);
  },
  async schemas() {
    return axios
      .get(url("schemas"))
      .then(return_data);
  },
  async map() {
    return axios
      .get(url("map"))
      .then(return_data);
  },
  async normalize_config(config) {
    return axios
      .post(url("normalize_config"), { config: config })
      .then(return_data);
  },
  async get_settings() {
    return axios
      .get(url("get_settings"))
      .then(return_data);
  },
  async set_settings(settings) {
    return axios
      .post(url("set_settings"), { settings: settings })
      .then(return_data);
  },
  log() {
    // todo: add link to where this was copied from!
    const xhr = new XMLHttpRequest();
    xhr.open("GET", url("log"));
    xhr.send();

    return xhr;
  },
  async stop_log() {
    return axios
      .put(url("stop_log"))
      .then(return_success);
  },
  events(onmessage, onerror, onopen) {
    // console.log(`registering EventSource for /api/events`);

    let evl = new EventSource(url("events"));
    evl.addEventListener("message", onmessage);

    if (onerror !== undefined) {
      evl.addEventListener("error", onerror);
    }
    if (onopen) {
      evl.addEventListener("open", onopen);
    }

    // console.log(evl);
    return evl;
  },
  async stop_events() {
    // console.log("url.close_events()");
    return axios
      .post(url("stop_events"))
      .then(return_success);
  },
  fs: {
    async select_video() {
      return axios
        .get(url("fs", "select_video"))
        .then(return_data);
    },
    async select_design() {
      return axios
        .get(url("fs", "select_design"))
        .then(return_data);
    },
    async check_video(video_path) {
      return axios
        .put(url("fs", "check_video"), { path: video_path })
        .then(return_data);
    },
    async check_design(design_path) {
      return axios
        .put(url("fs", "check_design"), { path: design_path })
        .then(return_data);
    },
    async open_root() {
      return axios
        .post(url("fs", 'open_root'))
        .then(return_data)
    },
  },
  db: {
    async forget() {
      return axios
        .post(url("db", "forget"))
        .then(return_success);
    },
    async get_result_list(analysis) {
      return axios
        .post(url("db", "get_result_list"), { analysis: analysis })
        .then(return_data);
    },
    async get_result(analysis, run) {
      return axios
        .post(url("db", "get_result"), { analysis: analysis, run: run })
        .then(return_data);
    },
    async export_result(analysis, run) {
      return axios
        .post(url('db', 'export_result'), { analysis: analysis, run: run })
        .then(return_data)
    },
    async get_recent_paths() {
      return axios
        .get(url("db", "get_recent_paths"))
        .then(return_data);
    },
  },
  cache: {
    async clear() {
      return axios
        .post(url("cache", "clear"))
        .then(return_success);
    },
    async size() {
      return axios
        .get(url("cache", "size"))
        .then(return_data);
    },
  },
  va: {
    async init() {
      // initialize an Analyzer in the backend & return its id
      return axios
        .post(url("va", "init"))
        .then(return_data);
    },
    async close(id) {
      return axios
        .post(url("va", "close"), { id: id })
        .then(return_success);
    },
    async state() {
      return axios
        .get(url("va", "state"))
        .then(return_data);
    },
    async stream_stop(id, endpoint) {
      return axios
        .post(url(`va/stream_stop?id=${id}&endpoint=${endpoint}`))
        .then(return_success);
    },
    async start(ids) {
      return axios
        .post(url("va", "start"), { queue: ids })
        .then(return_data);
    },
    async stop() {
      return axios
        .post(url("va", "stop"))
        .then(return_data);
    },
    __id__: {
      async cancel(id) {
        return axios
          .post(url("va", id, "cancel"))
          .then(return_data);
      },
      async get_total_time(id) {
        return axios
          .get(url("va", id, "get_total_time"))
          .then(return_data);
      },
      async get_config(id) {
        return axios
          .get(url("va", id, "get_config"))
          .then(return_data);
      },
      async get_colors(id) {
        return axios
          .get(url("va", id, "get_colors"))
          .then(return_data);
      },
      async get_status(id) {
        return axios
          .get(url("va", id, "status"))
          .then(return_data);
      },
      async get_relative_roi(id) {
        return axios
          .get(url("va", id, "get_relative_roi"))
          .then(return_data);
      },
      async set_config(id, config) {
        return axios
          .post(url("va", id, "set_config"), { config: config })
          .then(return_data)
          .catch();
      },
      async state_transition(id) {
        return axios
          .post(url("va", id, "state_transition"))
          .then(return_data);
      },
      async launch(id) {
        return axios
          .get(url("va", id, "can_launch"))
          .then((response) => {
            if (response.status === 200) {
              return axios.post(url("va", id, "launch")).then(return_data);
            } else {
              return false;
            }
          });
      },
      async seek(id, position) {
        // console.log(`url.seek(${id}), ${position}`);
        return axios
          .post(url("va", id, "seek"), { position: position })
          .then(return_data);
      },
      async get_seek_position(id) {
        return axios
          .get(url("va", id, "get_seek_position"))
          .then(return_data);
      },
      async estimate_transform(id, roi) {
        return axios
          .post(url("va", id, "estimate_transform"), { roi: roi })
          .then(return_success);
      },
      async turn_cw(id) {
        return axios
          .post(url("va", id, "turn_cw"))
          .then(return_success);
      },
      async turn_ccw(id) {
        return axios
          .post(url("va", id, "turn_ccw"))
          .then(return_success);
      },
      async flip_h(id) {
        return axios
          .post(url("va", id, "flip_h"))
          .then(return_success);
      },
      async flip_v(id) {
        return axios
          .post(url("va", id, "flip_v"))
          .then(return_success);
      },
      async clear_roi(id) {
        return axios
          .post(url("va", id, "clear_roi"))
          .then(return_success);
      },
      async get_db_id(id) {
        return axios
          .get(url("va", id, "get_db_id"))
          .then(return_data);
      },
      async undo_config(id, context = null) {
        return axios
          .put(url("va", id, "undo_config"), { context: context })
          .then(return_data);
      },
      async redo_config(id, context = null) {
        return axios
          .put(url("va", id, "redo_config"), { context: context })
          .then(return_data);
      },
      async set_filter(id, relative_coordinate) {
        return axios
          .post(url("va", id, "set_filter_click"), {
            relative_x: relative_coordinate.x,
            relative_y: relative_coordinate.y,
          })
          .then(return_data);
      },
      async clear_filters(id) {
        return axios
          .post(url("va", id, "clear_filters"))
          .then(return_success);
      },
      async commit(id) {
        return axios
          .post(url("va", id, "commit"))
          .then(return_success);
      },
      async analyze(id) {
        return axios.
        put(url("va", id, "analyze"))
          .then(return_success);
      },
    },
  },
};
