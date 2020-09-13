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
  get_app_state,
  set_config,
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
};

export const state = () => {
  return {
    last_heard_from_backend: null,
    queue: [], // array of analyzer ids (uuid strings)
    queue_state: QueueState.STOPPED,
    status: {}, // id: analyzer status object
    config: {}, // id: analyzer config object
    result: {},
    source: {},
    notices: [],
  };
};

export const mutations = {
  backendIsUp(state) {
    state.last_heard_from_backend = Date.now();
  },
  setSource(state, { source }) {
    try {
      assert(!(source === undefined), "no source provided");
      state.source = source;
    } catch (err) {
      console.warn(`setSource failed: '${source}'`);
      console.warn(err);
    }
  },

  closeSource(state) {
    try {
      if (!isEmpty(state.source)) {
        state.source.close();
        state.source = {};
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
    console.log("analyzers/setAnalyzerConfig");
    console.log(id);
    console.log(config);
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
    console.log("analyzers/newNotice");
    console.log(id);
    console.log(notice);

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
    console.log("analyzers/dismissNotice");
    console.log(notice);

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
};

export const getters = {
  getLastBackendContact: (state) => {
    return state.last_heard_from_backend;
  },
  getQueue: (state) => {
    // Clone instead of returning reference
    return [...state.queue];
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
    return isEmpty(state.source) && state.source.readyState !== 2;
  },
  getNotices: (state) => {
    return state.notices;
  },
};

export const actions = {
  source({ commit, getters }) {
    if (getters["hasSource"]) {
      commit("closeSource");
    }
    commit("setSource", {
      source: events(function (message) {
        commit("backendIsUp");
        try {
          let event = JSON.parse(message.data);

          assert(event.hasOwnProperty("category"));
          assert(includes(EVENT_CATEGORIES, event.category));
          assert(event.hasOwnProperty("id"));
          assert(event.hasOwnProperty("data"));

          console.log(`${event.category} event:`);
          console.log(event);

          commit(CATEGORY_COMMIT[event.category], {
            id: event.id,
            [event.category]: event.data,
          });
        } catch (err) {
          console.warn(`backend event callback failed`);
          console.warn(err);
        }
      }),
    });
  },

  async queue({ commit, dispatch }, { id }) {
    console.log(`action: analyzers.queue (id=${id})`);
    commit("addAnalyzer", { id: id });
    commit("addToQueue", { id: id });
  },

  unqueue({ commit }, { id }) {
    console.log(`action: analyzers.unqueue (id=${id})`);
    commit("dropFromQueue", { id: id });
    commit("dropAnalyzer", { id: id });
  },

  async init({ commit, dispatch }, { config = {} }) {
    // console.log(`action: analyzers.init`);
    return init().then((id) => {
      commit("backendIsUp");
      // console.log(`action: analyzers.init -- callback ~ api.init (id=${id})`);
      return dispatch("queue", { id: id }).then(() => {
        // console.log(
        //   `action: analyzers.init -- callback ~ analyzers.queue (id=${id})`
        // );
        return dispatch("set_config", { id: id, config: config }).then(
          (config) => {
            // console.log(
            //   `action: analyzers.init -- callback ~ analyzers.set_config (id=${id})`
            // );
            return launch(id).then((ok) => {
              commit("backendIsUp");
              // console.log(
              //   `action: analyzers.init -- callback ~ api.launch (id=${id})`
              // );
              if (ok) {
                console.log(`Launched '${id}'`);
                return id;
              } else {
                dispatch("unqueue", { id: id });
                console.warn(`Could not launch '${id}'`);
              }
              dispatch("sync");
            });
          }
        );
      });
    });
  },

  async sync({ commit, dispatch, getters }) {
    try {
      // console.log(`action: analyzers.sync`);

      if (!getters["hasSource"]) {
        dispatch("source");
      }

      return await get_app_state().then((app_state) => {
        commit("backendIsUp");
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
      });
    } catch (e) {
      console.warn("backend may be down; refresh to check again");
      return false;
    }
  },

  async get_config({ commit }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      // console.log(`action: analyzers.get_config (id=${id})`);

      return get_config(id).then((config) => {
        commit("backendIsUp");
        // console.log(
        //   `action: analyzers.get_config -- callback ~ api.get_config (id=${id})`
        // );
        commit("setAnalyzerConfig", {
          id: id,
          config: config,
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not get config for ${id}`);
      return undefined;
    }
  },

  async refresh({ getters, dispatch }, { id }) {
    try {
      assert(id !== undefined, "no id provided");
      console.log(`action: analyzers.refresh (id=${id})`);

      if (getters["getAnalyzerConfig"](id) === undefined) {
        dispatch("get_config", { id: id });
      }
      if (getters["getAnalyzerStatus"](id) === undefined) {
        dispatch("get_status", { id: id });
      }
      return;
    } catch (e) {}
  },

  async get_status({ commit }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      // console.log(`action: analyzers.get_status (id=${id})`);

      return get_status(id).then((status) => {
        commit("backendIsUp");
        // console.log(
        //   `action: analyzers.get_status -- callback ~ api.get_status (id=${id})`
        // );
        commit("setAnalyzerStatus", { id: id, status: status });
      });
    } catch (e) {
      console.warn(`could not get status for ${id}`);
      return undefined;
    }
  },

  async set_config({ commit }, { id, config }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(config === undefined), "no config");
      // console.log(`action: analyzers.set_config (id=${id})`);

      return set_config(id, config).then((config) => {
        commit("backendIsUp");
        // console.log(
        //   `action: analyzers.set_config -- callback ~ api.set_config (id=${id})`
        // );
        commit("setAnalyzerConfig", {
          id: id,
          config: config,
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not set config for ${id}`);
      return undefined;
    }
  },

  async turn({ commit, getters }, { id, direction }) {
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

      set_config(id, config).then((config) => {
        commit("backendIsUp");
        // console.log(
        //   `action: analyzers.set_config -- callback ~ api.set_config (id=${id})`
        // );
        commit("setAnalyzerConfig", {
          id: id,
          config: config,
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not turn ${id}`);
    }
  },
};
