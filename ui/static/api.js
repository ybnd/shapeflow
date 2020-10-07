import axios from "axios";

export { axios };

const CONFIG = {
  // proxy: {
  //   host: 'localhost',
  //   port: 7951,
  // }
};

export function api() {
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

export async function ping() {
  return axios
    .get(api("ping"), CONFIG)
    .then(return_success)
    .catch((e) => {
      return false;
    });
}

export function unload() {
  // axios can't be called on page unload, use sendBeacon instead
  try {
    return navigator.sendBeacon(api("unload"));
  } catch (e) {
    // navigator is not defined in Jest
    console.warn(e)
    return axios.post(api('unload'), {}, CONFIG)
  }
}

export function quit() {
  return axios.post(api("quit"), {}, CONFIG).then(return_success)
}

export async function restart() {
  return axios.post(api("restart"), {}, CONFIG).then(return_data);
}

export async function settings_schema() {
  return axios.get(api("settings_schema"), CONFIG).then(return_data);
}

export async function get_settings() {
  return axios.get(api("get_settings"), CONFIG).then(return_data);
}

export async function set_settings(settings) {
  return axios
    .post(api("set_settings"), { settings: settings }, CONFIG)
    .then(return_data);
}

export async function get_app_state() {
  return axios.get(api("app_state"), CONFIG).then(return_data);
}

export async function init() {
  // initialize an Analyzer in the backend & return its id
  return axios.post(api("init"), {}, CONFIG).then(return_data);
}

export async function close(id) {
  return axios.post(api(id, "close"), {}, CONFIG).then(return_success);
}

export async function cancel(id) {
  return axios.post(api(id, "cancel"), {}, CONFIG).then(return_data);
}

export async function get_schemas() {
  return axios.get(api("schemas"), CONFIG).then(return_data);
}

export async function select_video_path() {
  return axios.get(api("select_video_path"), CONFIG).then(return_data);
}

export async function select_design_path() {
  return axios.get(api("select_design_path"), CONFIG).then(return_data);
}

export async function check_video_path(video_path) {
  return axios
    .put(api("check_video_path"), { video_path: video_path }, CONFIG)
    .then(return_data);
}

export async function check_design_path(design_path) {
  return axios
    .put(api("check_design_path"), { design_path: design_path }, CONFIG)
    .then(return_data);
}

export async function open_root() {
  return axios.post(api('open_root'), {}, CONFIG).then(return_data)
}

export async function get_total_time(id) {
  return axios.get(api(id, "call/get_total_time"), CONFIG).then(return_data);
}

export async function get_config(id) {
  return axios.get(api(id, "call/get_config"), CONFIG).then(return_data);
}

export async function get_colors(id) {
  return axios.get(api(id, "call/get_colors"), CONFIG).then(return_data);
}

export async function get_state(id) {
  return axios.get(api(id, "get_state"), CONFIG).then(return_data);
}

export async function get_status(id) {
  return axios.get(api(id, "call/status"), CONFIG).then(return_data);
}

export async function get_relative_roi(id) {
  return axios.get(api(id, "call/get_relative_roi"), CONFIG).then(return_data);
}

export async function set_config(id, config) {
  return axios
    .post(api(id, "call/set_config"), { config: config }, CONFIG)
    .then(return_data)
    .catch();
}

export async function state_transition(id) {
  return axios.post(api(id, "call/state_transition"), {}, CONFIG).then(return_data);
}

export async function launch(id) {
  return axios.get(api(id, "call/can_launch"), CONFIG).then((response) => {
    if (response.status === 200) {
      return axios.post(api(id, "launch")).then(return_data);
    } else {
      return false;
    }
  });
}

export async function seek(id, position) {
  // console.log(`api.seek(${id}), ${position}`);
  return axios
    .post(api(id, "call/seek"), { position: position }, CONFIG)
    .then(return_data);
}

export async function get_seek_position(id) {
  return axios.get(api(id, "call/get_seek_position"), CONFIG).then(return_data);
}

export async function estimate_transform(id, roi) {
  return axios
    .post(api(id, "call/estimate_transform"), { roi: roi }, CONFIG)
    .then(return_success);
}

export async function turn_cw(id) {
  return axios.post(api(id, "call/turn_cw"), CONFIG).then(return_success);
}

export async function turn_ccw(id) {
  return axios.post(api(id, "call/turn_ccw"), CONFIG).then(return_success);
}

export async function flip_h(id) {
  return axios.post(api(id, "call/flip_h"), CONFIG).then(return_success);
}

export async function flip_v(id) {
  return axios.post(api(id, "call/flip_v"), CONFIG).then(return_success);
}

export async function clear_roi(id) {
  return axios.post(api(id, "call/clear_roi"), CONFIG).then(return_success);
}

export async function get_db_id(id) {
  return axios.get(api(id, "call/get_db_id"), CONFIG).then(return_data);
}

export async function undo_config(id, context = null) {
  return axios
    .put(api(id, "call/undo_config"), { context: context }, CONFIG)
    .then(return_data);
}

export async function redo_config(id, context = null) {
  return axios
    .put(api(id, "call/redo_config"), { context: context }, CONFIG)
    .then(return_data);
}

export async function set_filter(id, relative_coordinate) {
  return axios
    .post(api(id, "call/set_filter_click"), {
      relative_x: relative_coordinate.x,
      relative_y: relative_coordinate.y,
    }, CONFIG)
    .then(return_data);
}

export async function clear_filters(id) {
  return axios.post(api(id, "call/clear_filters"), {}, CONFIG).then(return_success);
}

export async function commit(id) {
  return axios.post(api(id, "call/commit"), {}, CONFIG).then(return_success);
}

export async function analyze(id) {
  return axios.put(api(id, "call/analyze"), CONFIG).then(return_success);
}

export function get_log() {
  // todo: add link to where this was copied from!
  var xhr = new XMLHttpRequest();  // todo: integrate CONFIG somehow
  xhr.open("GET", api("get_log"));
  xhr.send();

  return xhr;
}

export async function stop_log() {
  return axios.put(api("stop_log"), {}, CONFIG).then(return_success);
}

export async function stop_stream(id, endpoint) {
  return axios.post(api("stream", id, endpoint, "stop"), {}, CONFIG).then(return_success);
}

export function events(onmessage, onerror, onopen) {
  // console.log(`registering EventSource for /api/stream/events`);

  let evl = new EventSource(api("stream", "events"));  // todo: integrate CONFIG somehow
  evl.addEventListener("message", onmessage);

  if (onerror !== undefined) {
    evl.addEventListener("error", onerror);
  }
  if (onopen) {
    evl.addEventListener("open", onopen);
  }

  // console.log(evl);
  return evl;
}

export function close_events() {
  // console.log("api.close_events()");
  return axios.post(api("stream", "events", "stop"), {}, CONFIG).then(return_success);
}

export async function clear_cache() {
  return axios.post(api("cache", "clear"), {}, CONFIG).then(return_success);
}

export async function get_cache_size() {
  return axios.get(api("cache", "disk-size"), CONFIG).then(return_data);
}

export async function clear_db() {
  return axios.post(api("db", "forget"), {}, CONFIG).then(return_success);
}

export async function get_db_size() {
  return axios.get(api("db", "disk-size"), CONFIG).then(return_data);
}

export async function get_result_list(analysis) {
  return axios
  .post(api("db", "get_result_list"), { analysis: analysis }, CONFIG)
    .then(return_data);
}

export async function get_result(analysis, run) {
  return axios
    .post(api("db", "get_result"), { analysis: analysis, run: run }, CONFIG)
    .then(return_data);
}

export async function export_result(analysis, run) {
  return axios.post(api('db', 'export_result'), { analysis: analysis, run: run }, CONFIG).then(return_data)
}


export async function get_recent_paths() {
  return axios.get(api("db", "get_recent_paths"), CONFIG).then(return_data);
}

export async function q_start(ids) {
  return axios.post(api("start"), { queue: ids }, CONFIG).then(return_data);
}

export async function q_stop() {
  return axios.post(api("stop"), {}, CONFIG).then(return_data);
}
