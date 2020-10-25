import {
  EVENT_CATEGORIES,
  NOTICE_LIMIT,
  QueueState,
  api
} from "@/api";

import { uuidv4 } from "@/util";

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

export const MAX_TIME_WITHOUT_CONTACT = 1500;
export const SYNC_INTERVAL = 1000;

const OPENED_AT = Date.now();
export const LOAD_INTERVAL = 1000;

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
    interval: null,
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

      if (!(id in state.status) && !(id in state.config)) {
        state.status = { ...state.status, [id]: {} };
        state.config = { ...state.config, [id]: {} };
      } else {
        console.warn(`addAnalyzer: '${id}' already defined`);
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
    try {
      assert(notice !== undefined, "no notice provided");
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
    } catch(err) {
      console.warn(`newNotice failed: '${id}', notice: `);
      console.warn(notice);
      console.warn(err);
    }
  },
  dismissNotice(state, { notice }) {
    // console.log("analyzers/dismissNotice");
    // console.log(notice);

    try {
      assert(notice !== undefined, "no notice provided");
      const index = state.notices.findIndex((e) => e === notice);
      if (index !== -1) {
        state.notices.splice(index, 1);
      }
    } catch(err) {
      console.warn(`dismissNotice failed: notice: `);
      console.warn(notice);
      console.warn(err);
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
        state.queue.splice(state.queue.indexOf(id), 1);
      }
    } catch (err) {
      console.warn(`dropFromQueue failed: '${id}'`);
      console.warn(err);
    }
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
  isValidId: (state) => (id) => {
    if (Math.abs(Date.now() - OPENED_AT) > LOAD_INTERVAL) {
      return state.queue.indexOf(id) !== -1;
    } else {
      return undefined;
    }
  },
  getFullStatus: (state) => {
    return state.status;
  },
  getAnalyzerStatus: (state) => (id) => {
    if (id in state.status) {
      return state.status[id];
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

    return api.stop_events().then((ok) => {
      dispatch("connection", { ok: ok });
      commit("closeSource");

      if (ok) {
        commit("setSource", {
          source: api.events(
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
              // console.log("backend event source opened");
              // console.log(target);
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
    commit("setQueueState", { queue_state: QueueState.RUNNING });
    return api.va.start(getters["getQueue"])
      .then((app_state) => {
        dispatch("connection", { ok: true });
        commit("setQueueState", { queue_state: app_state.q_state });
      })
      .catch((reason) => {
        console.warn(reason);
        dispatch("connection", { ok: false });
      });
  },

  q_stop({ commit, dispatch }) {
    // console.log("action: analyzers.q_stop");
    // shouldn't commit 'setQueueState' before callback; buttons may flash otherwise
    return api.va.stop()
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
      // console.log(id);
      await dispatch("close", { id: id });
    }
  },

  async init({ commit, dispatch }, { config = {} }) {
    // console.log(`action: analyzers.init`);
    return api.va.init().then((id) => {
      dispatch("connection", { ok: true });
      dispatch("queue", { id: id });
      // console.log(`action: analyzers.init -- callback ~ url.init (id=${id})`);
      return dispatch("set_config", { id: id, config: config })
        .then((config) => {
          // console.log(
          //   `action: analyzers.init -- callback ~ analyzers.set_config (id=${id})`
          // );
          return api.va.__id__.launch(id).then((ok) => {
            dispatch("connection", { ok: true });
            // console.log(
            //   `action: analyzers.init -- callback ~ url.launch (id=${id})`
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
        .catch((error) => {  // todo: does this catch anything really?
          console.warn(
            "aborted 'analyzers/init' before 'analyzers/launch' call." // todo: should close analyzer!
          );
          dispatch("close", { id: id }).then((ok) => {
            if (ok) {
              return undefined;
            } else {
              throw error;
            }
          });
        });
    });
  },

  async close({ commit, dispatch }, { id }) {
    try {
      // console.log(`action: analyzers/close (id=${id})`);
      assert(!(id === undefined), "no id provided");

      return api.va.close(id).then((ok) => {
        // console.log("close action callback");
        dispatch("unqueue", { id: id });
        return ok;
      });
    } catch (err) {
      console.warn(`could not close ${id}`);
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

      return await api.va.state()
        .then((app_state) => {
          dispatch("connection", { ok: true });
          // console.log(`action: analyzers.sync -- callback ~ url.get_app_state`);

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
                  dispatch("get_config", { id: app_state.ids[i] });  // todo: this may be unnecessary, seems to be covered by the dispatch below.
                });
              }
              commit("setAnalyzerStatus", {
                id: app_state.ids[i],
                status: app_state.status[i],
              });
            }
          }

          // for any id with get_config[id] is undefined, dispatch get_config
          q = getters["getQueue"];
          for (let i = 0; i < q.length; i++) {
            if (isEmpty(getters["getAnalyzerConfig"](q[i]))) {
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

      return api.va.__id__.get_config(id)
        .then((config) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.get_config -- callback ~ url.get_config (id=${id})`
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

      if (Object.keys(getters["getAnalyzerConfig"](id)).length === 0) {
        await dispatch("get_config", { id: id });
      }
      if (Object.keys(getters["getAnalyzerStatus"](id)).length === 0) {
        await dispatch("get_status", { id: id });
      }
    } catch (e) {}
  },

  async get_status({ commit, dispatch }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      // console.log(`action: analyzers.get_status (id=${id})`);

      return api.va.__id__.get_status(id)
        .then((status) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.get_status -- callback ~ url.get_status (id=${id})`
          // );
          commit("setAnalyzerStatus", { id: id, status: status });
          return status;
        })
        .catch((reason) => {  // todo: when does this catch exactly?
          dispatch("connection", { ok: false });
          return undefined;
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

      return api.va.__id__.set_config(id, config)
        .then((config) => {
          dispatch("connection", { ok: true });
          // console.log(
          //   `action: analyzers.set_config -- callback ~ url.set_config (id=${id})`
          // );
          commit("setAnalyzerConfig", {
            id: id,
            config: config,
          });
          return config;
        })
        .catch((error) => {  // todo: when does this catch exactly?
          console.warn(`/api/${id}/set_config failed`);
          dispatch("connection", { ok: false });
          throw error;
        });
    } catch (e) {
      console.warn(`could not set config for ${id}`);
      return undefined;
    }
  },

  // todo: add undo_config
  // todo: add redo_config
};
