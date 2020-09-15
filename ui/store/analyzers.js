import Vue from "vue";
import {
  EVENT_CATEGORIES,
  NOTICE_LIMIT,
  QueueState,
  events,
  get_config,
  get_status,
  init,
  launch,
  remove,
  get_app_state,
  set_config,
  close_events,
  q_start,
  q_stop,
} from "../static/api";

import { uuidv4 } from "../static/util";

import assert from "assert";

import isEmpty from "lodash/isEmpty";
import includes from "lodash/includes";
import cloneDeep from "lodash/cloneDeep";

const CATEGORY_COMMIT = {
  status: "setAnalyzerStatus",
  config: "setAnalyzerConfig",
  notice: "newNotice",
  close: "closeSource",
};

const MAX_TIME_WITHOUT_CONTACT = 1500;
const SYNC_INTERVAL = 1000;

export const state = () => {
  return {
    last_heard_from_backend: null,
    is_connected: false,
    queue: [], // array of analyzer ids (uuid strings)
    queue_state: QueueState.STOPPED,
    status: {}, // id: analyzer status object
    config: {}, // id: analyzer config object
    result: {},
    source: null,
    notices: [],
    interval: [],
  };
};

export const mutations = {
  backendIsUp(state) {
    state.last_heard_from_backend = Date.now();
  },
  setIsConnected(state, { connected }) {
    state.is_connected = connected;
  },
  setSource(state, { source }) {
    // console.log("analyzers/setSource");
    try {
      assert(!(source === undefined), "no source provided");
      state.source = source;
      // console.log(state.source);
    } catch (err) {
      console.warn(`setSource failed: '${source}'`);
      console.warn(err);
    }
  },

  closeSource(state) {
    // console.log("analyzers/closeSource");
    try {
      if (state.source !== null) {
        state.source.close();
        state.source = null;
      }
    } catch (err) {
      console.warn(`closeSource failed`);
      console.warn(err);
    }
  },
  setQueueState(state, { queue_state }) {
    try {
      assert(!(queue_state === undefined), "no queue_state provided");

      state.queue_state = queue_state;
    } catch (err) {
      console.warn(`setQueueState failed: '${queue_state}'`);
      console.warn(err);
    }
  },
  addAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      if (!(id in state)) {
        state.status = { ...state.config, [id]: {} };
        state.config = { ...state.status, [id]: {} };
      } else {
        console.warn(`addAnalyzerState: '${id}' already defined`);
      }
    } catch (err) {
      console.warn(`addAnalyzer failed: '${id}'`);
      console.warn(err);
    }
  },

  setAnalyzerStatus(state, { id, status }) {
    // console.log("analyzers/setAnalyzerStatus");
    // console.log(id);
    // console.log(status);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(status === undefined), "no status");

      state.status[id] = {
        ...state.status[id],
        ...status,
      };
    } catch (err) {
      console.warn(`setAnalyzerStatus failed: '${id}', status: `);
      console.warn(status);
      console.warn(err);
    }
  },

  setAnalyzerConfig(state, { id, config }) {
    // console.log("analyzers/setAnalyzerConfig");
    // console.log(id);
    // console.log(config);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(config === undefined), "no config");

      state.config[id] = {
        ...state.config[id],
        ...config,
      };

      if (!(config.name === undefined)) {
        state.config[id].name = config.name;
      } else {
        state.config[id].name = "!! unnamed !!";
        console.warn(`setAnalyzerConfig: using default name for '${id}'`);
      }
    } catch (err) {
      console.warn(`setAnalyzerConfig failed: '${id}', config: `);
      console.warn(config);
      console.warn(err);
    }
  },
  newNotice(state, { id, notice }) {
    // console.log("analyzers/newNotice");
    // console.log(id);
    // console.log(notice);

    let name = undefined;

    if (id !== undefined) {
      if (state.config[id] !== undefined && !isEmpty(state.config[id].name)) {
        name = state.config[id].name;
      }
    }

    if (!notice.uuid) {
      // no uuid specified -> generate
      notice = { ...notice, analyzer: name, uuid: uuidv4() };
      state.notices.push(notice);
    } else {
      // uuid specified -> only push if it hasn't been pushed yet
      const index = state.notices.findIndex((e) => e.uuid === notice.uuid);
      if (index === -1) {
        state.notices.push(notice);
      }
    }

    state.notices = state.notices.slice(-NOTICE_LIMIT);
  },
  dismissNotice(state, { notice }) {
    // console.log("analyzers/dismissNotice");
    // console.log(notice);

    const index = state.notices.findIndex((e) => e === notice);
    if (index !== -1) {
      state.notices.splice(index, 1);
    }
  },
  dropAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      if (id in state.status) {
        delete state.status[id];
      }
      if (id in state.config) {
        delete state.config[id];
      }
    } catch (err) {
      console.warn(`dropAnalyzer failed: '${id}'`);
      console.warn(err);
    }
  },
  addToQueue(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (!state.queue.includes(id)) {
        state.queue = [...state.queue, id];
      }
    } catch (err) {
      console.warn(`addToQueue failed: '${id}'`);
      console.warn(err);
    }
  },
  dropFromQueue(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (state.queue.includes(id)) {
        state.queue.splice(state.queue.indexOf(id, 1));
      }
    } catch (err) {
      console.warn(`dropFromQueue failed: '${id}'`);
      console.warn(err);
    }
  },
  clearQueue(state) {
    state.queue = [];
  },
  setQueue(state, { queue }) {
    state.queue = queue;
  },
  setInterval(state, { interval }) {
    state.interval = interval;
  },
};

export const getters = {
  getLastBackendContact: (state) => {
    return state.last_heard_from_backend;
  },
  isConnected: (state) => {
    return state.is_connected;
  },
  getQueue: (state) => {
    // Clone instead of returning reference
    return cloneDeep(state.queue);
  },
  getQueueState: (state) => {
    return state.queue_state;
  },
  getIndex: (state) => (id) => {
    return state.queue.indexOf(id);
  },
  getFullStatus: (state) => {
    return state.status;
  },
  getAnalyzerStatus: (state) => (id) => {
    if (id in state.status) {
      return state.status[id];
    }
  },
  getResult: (state) => (id) => {
    if (id in state.result) {
      return state.result[id];
    }
  },
  getAnalyzerConfig: (state) => (id) => {
    return state.config[id];
  },
  getAnalyzerConfigCopy: (state) => (id) => {
    return cloneDeep(state.config[id]);
  },
  getFeatures: (state) => (id) => {
    return state.config[id].features;
  },
  getMasks: (state) => (id) => {
    return state.config[id]["masks"];
  },
  getRoi: (state) => (id) => {
    return state.config[id].transform.roi;
  },
  getName: (state) => (id) => {
    if (id !== undefined) {
      if (state.config[id] !== undefined && !isEmpty(state.config[id].name)) {
        return state.config[id].name;
      }
    }
  },
  hasSource: (state) => {
    // console.log("analyzers/hasSource");
    // console.log(state.source);

    let has_source;
    if (state.source !== null) {
      has_source =
        !state.source.hasOwnProperty("url") && state.source.readyState !== 2;
    } else {
      has_source = false;
    }

    // console.log(has_source);
    return has_source;
  },
  getNotices: (state) => {
    return state.notices;
  },
  getInterval: (state) => {
    return state.interval;
  },
};

export const actions = {
  loop({ commit, dispatch }) {
    dispatch("sync");
    commit("setInterval", {
      interval: setInterval(() => {
        dispatch("sync");
      }, SYNC_INTERVAL),
    });
  },

  stop({ getters }) {
    clearInterval(getters["getInterval"]);
  },

  connection({ commit, getters }, { ok }) {
    // console.log("analyzers/connection");
    if (ok) {
      // console.log("up");
      commit("backendIsUp");
      commit("setIsConnected", { connected: true });
    } else if (
      Date.now() - getters["getLastBackendContact"] <
      MAX_TIME_WITHOUT_CONTACT
    ) {
      // console.log("up...");
      commit("setIsConnected", { connected: true });
    } else {
      // console.log("down");
      commit("setIsConnected", { connected: false });
    }
  },

  async source({ commit, getters, dispatch }) {
    // console.log("analyzers/source");

    return close_events().then((ok) => {
      dispatch("connection", { ok: ok });
      commit("closeSource");

      if (ok) {
        commit("setSource", {
          source: events(
            function (message) {
              dispatch("connection", { ok: ok });

              // console.log(message);

              try {
                let event = JSON.parse(message.data);

                assert(event.hasOwnProperty("category"));
                assert(includes(EVENT_CATEGORIES, event.category));
                assert(event.hasOwnProperty("id"));
                assert(event.hasOwnProperty("data"));

                // console.log(`${event.category} event:`);
                // console.log(event);

                commit(CATEGORY_COMMIT[event.category], {
                  id: event.id,
                  [event.category]: event.data,
                });
              } catch (err) {
                console.warn(`backend event callback failed`);
                console.warn(err);
              }
            },
            function (target) {
              console.warn("backend event error something something");
              console.warn(target);
              // dispatch("source");
            },
            function ({ target }) {
              console.log("backend event source opened");
              console.log(target);
            }
          ),
        });
      }
    });
  },

  async queue({ commit, dispatch }, { id }) {
    // todo: doesn't need to be async
    // console.log(`action: analyzers.queue (id=${id})`);
    commit("addAnalyzer", { id: id });
    commit("addToQueue", { id: id });
  },

  unqueue({ commit }, { id }) {
    // console.log(`action: analyzers.unqueue (id=${id})`);
    commit("dropFromQueue", { id: id });
    commit("dropAnalyzer", { id: id });
  },

  q_start({ commit, getters, dispatch }) {
    // console.log("action: analyzers.q_start");
    return q_start(getters["getQueue"])
      .then((app_state) => {
        dispatch("connection", { ok: true });
        commit("setQueueState", { queue_state: app_state.q_state });
      })
      .catch((reason) => {
        dispatch("connection", { ok: false });
      });
  },

  q_stop({ commit, dispatch }) {
    // console.log("action: analyzers.q_stop");
    return q_stop()
      .then((app_state) => {
        dispatch("connection", { ok: true });
        commit("setQueueState", { queue_state: app_state.q_state });
      })
      .catch((reason) => {
        dispatch("connection", { ok: false });
      });
  },

  async q_clear({ commit, getters, dispatch }) {
    // console.log("action: analyzers.q_clear");
    const queue = getters["getQueue"];
    for (var id of queue) {
      console.log(id);
      await dispatch("remove", { id: id });
    }
  },

  async init({ commit, dispatch }, { config = {} }) {
    // console.log(`action: analyzers.init`);
    return init()
      .then((id) => {
        dispatch("connection", { ok: true });
        // console.log(`action: analyzers.init -- callback ~ api.init (id=${id})`);
        return dispatch("queue", { id: id }).then(() => {
          // todo: only queue after set_config call
          // console.log(
          //   `action: analyzers.init -- callback ~ analyzers.queue (id=${id})`
          // );
          return dispatch("set_config", { id: id, config: config })
            .then((config) => {
              // console.log(
              //   `action: analyzers.init -- callback ~ analyzers.set_config (id=${id})`
              // );
              return launch(id).then((ok) => {
                dispatch("connection", { ok: true });
                // console.log(
                //   `action: analyzers.init -- callback ~ api.launch (id=${id})`
                // );
                if (ok) {
                  // console.log(`Launched '${id}'`);
                  return id;
                } else {
                  dispatch("unqueue", { id: id });
                  console.warn(`Could not launch '${id}'`);
                }
                dispatch("sync");
              });
            })
            .catch((error) => {
              console.warn(
                "aborted 'analyzers/init' before 'analyzers/launch' call." // todo: should remove analyzer!
              );
              dispatch("remove", { id: id }).then((ok) => {
                if (ok) {
                  return undefined;
                } else {
                  throw error;
                }
              });
            });
        });
      })
      .catch((reason) => {
        dispatch("connection", { ok: false });
      });
  },

  async remove({ commit, dispatch }, { id }) {
    try {
      console.log(`action: analyzers.remove (id=${id})`);
      assert(!(id === undefined), "no id provided");

      return remove(id).then((ok) => {
        console.log("remove action callback");
        dispatch("unqueue", { id: id });
        return ok;
      });
    } catch (err) {
      console.warn(`could not remove ${id}`);
      console.warn(err);
      return undefined;
    }
  },

  async sync({ commit, dispatch, getters }) {
    try {
      // console.log(`action: analyzers.sync`);

      if (!getters["hasSource"]) {
        dispatch("source");
      }

      return await get_app_state()
        .then((app_state) => {
          dispatch("connection", { ok: true });
          // console.log(`action: analyzers.sync -- callback ~ api.get_app_state`);

          commit("setQueueState", { queue_state: app_state.q_state });

          // unqueue old ids
          let q = getters["getQueue"];
          if (q.length > 0) {
            for (let i = 0; i < q.length; i++) {
              if (!app_state.ids.includes(q[i])) {
                dispatch("unqueue", { id: q[i] });
              }
            }
          }
          // queue new ids
          if (app_state.ids.length > 0) {
            let q = getters["getQueue"];
            for (let i = 0; i < app_state.ids.length; i++) {
              if (!q.includes(app_state.ids[i])) {
                dispatch("queue", { id: app_state.ids[i] }).then(() => {
                  // console.log(
                  //   `action: analyzers.sync -- callback ~ analyzers.queue (id=${ids[i]})`
                  // );
                  dispatch("get_config", { id: app_state.ids[i] });
                });
              }
              commit("setAnalyzerStatus", {
                id: app_state.ids[i],
                status: app_state.status[i],
              });
            }
          }

          // for any id with get_configconfig[id] is undefined, dispatch get_config
          q = getters["getQueue"];
          for (let i = 0; i < q.length; i++) {
            if (getters["getAnalyzerConfig"](q[i]) === undefined) {
              dispatch("get_config", { id: q[i] });
            }
          }

          return true;
        })
        .catch((reason) => {
          dispatch("connection", { ok: false });
        });
    } catch (e) {
      dispatch("connection", { ok: false });
      commit("closeSource");
      return false;
    }
  },

  async get_config({ commit, dispatch }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      // console.log(`action: analyzers.get_config (id=${id})`);

      return get_config(id)
        .then((config) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.get_config -- callback ~ api.get_config (id=${id})`
          // );
          commit("setAnalyzerConfig", {
            id: id,
            config: config,
          });
          return config;
        })
        .catch((reason) => {
          dispatch("connection", { ok: false });
        });
    } catch (e) {
      console.warn(`could not get config for ${id}`);
      return undefined;
    }
  },

  async refresh({ getters, dispatch }, { id }) {
    try {
      assert(id !== undefined, "no id provided");
      // console.log(`action: analyzers.refresh (id=${id})`);

      if (getters["getAnalyzerConfig"](id) === undefined) {
        dispatch("get_config", { id: id });
      }
      if (getters["getAnalyzerStatus"](id) === undefined) {
        dispatch("get_status", { id: id });
      }
      return;
    } catch (e) {}
  },

  async get_status({ commit, dispatch }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      // console.log(`action: analyzers.get_status (id=${id})`);

      return get_status(id)
        .then((status) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.get_status -- callback ~ api.get_status (id=${id})`
          // );
          commit("setAnalyzerStatus", { id: id, status: status });
        })
        .catch((reason) => {
          dispatch("connection", { ok: false });
        });
    } catch (e) {
      console.warn(`could not get status for ${id}`);
      return undefined;
    }
  },

  async set_config({ commit, dispatch }, { id, config }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(config === undefined), "no config");
      // console.log(`action: analyzers.set_config (id=${id})`);

      return set_config(id, config)
        .then((config) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.set_config -- callback ~ api.set_config (id=${id})`
          // );
          commit("setAnalyzerConfig", {
            id: id,
            config: config,
          });
          return config;
        })
        .catch((error) => {
          console.warn(`/api/${id}/set_config failed`);
          dispatch("connection", { ok: false });
          throw error;
        });
    } catch (e) {
      console.warn(`could not set config for ${id}`);
      return undefined;
    }
  },

  async turn({ commit, getters, dispatch }, { id, direction }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (direction === undefined) {
        direction = "CW";
      }

      let config = {
        transform: { turn: getters["getAnalyzerConfig"](id).transform.turn },
      };

      if (direction === "CW") {
        config.transform.turn += 1;
      } else if (direction === "CCW") {
        config.transform.turn -= 1;
      }

      set_config(id, config)
        .then((config) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.set_config -- callback ~ api.set_config (id=${id})`
          // );
          commit("setAnalyzerConfig", {
            id: id,
            config: config,
          });
          return config;
        })
        .catch((reason) => {
          dispatch("connection", { ok: false });
        });
    } catch (e) {
      console.warn(`could not turn ${id}`);
    }
  },
};
