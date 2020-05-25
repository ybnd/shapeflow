import Vue from "vue";
import {
  AnalyzerState as ast,
  get_config,
  set_config,
  get_state,
  get_schemas,
  init,
  list,
  launch,
  events,
  EVENT_CATEGORIES,
  get_status
} from "../static/api";

import assert from "assert";
import _ from "lodash";

const CATEGORY_COMMIT = {
  status: "setAnalyzerStatus",
  config: "setAnalyzerConfig",
  result: "updateAnalyzerResult"
};

export const state = () => {
  return {
    queue: [], // array of analyzer ids (uuid strings)
    status: {}, // id: analyzer status object
    config: {}, // id: analyzer config object
    result: {},
    source: {}
  };
};

export const mutations = {
  setSource(state, { source }) {
    try {
      assert(!(source === undefined), "no source provided");
      state.source = source;
    } catch (err) {
      console.warn(`setSource failed: '${id}'`);
      console.warn(err);
    }
  },

  closeSource(state) {
    try {
      if (!_.isEmpty(state.source)) {
        state.source.close();
        state.source = {};
      }
    } catch (err) {
      console.warn(`closeSource failed`);
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
        ...status
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
        ...config
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

  updateAnalyzerResult(state, { id, result }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(result === undefined), "no result");

      state.result[id] = {
        // todo: decide result format ~ plotting packages
        ...state.result[id], // todo: append result to state.result[id]
        ...result
      };
    } catch (err) {
      console.warn(`updateAnalyzerResult failed: '${id}', result: `);
      console.warn(result);
      console.warn(err);
    }
  },

  dropAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      state.source[id].status.close();
      state.source[id].config.close();

      delete state.status[id];
      delete state.config[id];
      delete state.source[id];
    } catch {
      `dropAnalyzer failed: '${id}'`;
    }
  },
  addToQueue(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (!state.queue.includes(id)) {
        state.queue = [...state.queue, id];
      }
    } catch {
      console.warn(`addToQueue failed: '${id}'`);
    }
  },
  dropFromQueue(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (state.queue.includes(id)) {
        Vue.set(state, "queue", state.queue.splice(state.queue.indexOf(id, 1))); // todo: probably wrong
      }
    } catch {
      console.warn(`dropFromQueue failed: '${id}'`);
    }
  },
  clearQueue(state) {
    state.queue = [];
  },
  setQueue(state, { queue }) {
    state.queue = queue;
  }
};

export const getters = {
  getQueue: state => {
    // Clone instead of returning reference
    return [...state.queue];
  },
  getIndex: state => id => {
    return state.queue.indexOf(id);
  },
  getFullStatus: state => {
    return state.status;
  },
  getStatus: state => id => {
    if (id in state.status) {
      return state.status[id];
    }
  },
  getConfig: state => id => {
    return state.config[id];
  },
  getFeatures: state => id => {
    return state.config[id].features;
  },
  getMasks: state => id => {
    return state.config[id].masks.map(({ name }) => name);
  },
  getMaskFilterType: state => (id, mask_index) => {
    // console.log(`getMaskFilterType: id=${id} mask_index=${mask_index}`);
    //
    // console.log("state.config[id].masks[mask_index] = ");
    // console.log(state.config[id].masks[mask_index]);

    return state.config[id].masks[mask_index].filter.type;
  },
  getMaskFilterData: state => (id, mask_index) => {
    // console.log(`getMaskFilterData: id=${id} mask_index=${mask_index}`);
    //
    // console.log("state.config[id].masks[mask_index] = ");
    // console.log(state.config[id].masks[mask_index]);

    return state.config[id].masks[mask_index].filter.data;
  },
  getMaskFilterParameters: state => (id, mask_index) => {
    // console.log(`getMaskFilterParameters: id=${id} mask_index=${mask_index}`);
    //
    // console.log("state.config[id].masks[mask_index] = ");
    // console.log(state.config[id].masks[mask_index]);

    return state.config[id].masks[mask_index].filter.parameters;
  },
  getRoi: state => id => {
    return state.config[id].transform.roi;
  },
  getName: state => id => {
    return state.config[id].name;
  },
  hasSource: state => {
    return _.isEmpty(state.source) && state.source.readyState !== 2;
  }
};

export const actions = {
  source({ commit, getters }) {
    if (getters["hasSource"]) {
      commit("closeSource");
    }
    commit("setSource", {
      source: events(function(message) {
        try {
          let event = JSON.parse(message.data);

          assert(event.hasOwnProperty("category"));
          assert(_.includes(EVENT_CATEGORIES, event.category));
          assert(event.hasOwnProperty("id"));
          assert(event.hasOwnProperty("data"));

          // console.log("/api/stream/events callback");
          // console.log(`category: ${event.category}`);
          // console.log(`id: ${event.id}`);
          // console.log("data: ");
          // console.log(event.data);

          commit(CATEGORY_COMMIT[event.category], {
            id: event.id,
            [event.category]: event.data
          });
        } catch (err) {
          console.warn(`backend event callback failed`);
          console.warn(err);
        }
      })
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
    console.log(`action: analyzers.init`);
    return init().then(id => {
      console.log(`action: analyzers.init -- callback ~ api.init (id=${id})`);
      return dispatch("queue", { id: id }).then(() => {
        console.log(
          `action: analyzers.init -- callback ~ analyzers.queue (id=${id})`
        );
        return dispatch("set_config", { id: id, config: config }).then(
          config => {
            console.log(
              `action: analyzers.init -- callback ~ analyzers.set_config (id=${id})`
            );
            return launch(id).then(ok => {
              console.log(
                `action: analyzers.init -- callback ~ api.launch (id=${id})`
              );
              if (ok) {
                console.log(`Launched '${id}'`);
                return id;
              } else {
                dispatch("unqueue", { id: id });
                console.warn(`Could not launch '${id}'`);
              }
            });
          }
        );
      });
    });
  },

  async sync({ dispatch, getters }) {
    console.log(`action: analyzers.sync`);
    try {
      if (!getters["hasSource"]) {
        dispatch("source");
      }
      return await list().then(ids => {
        console.log(`action: analyzers.sync -- callback ~ api.list`);
        // unqueue dead ids
        let q = getters["getQueue"];
        if (q.length > 0) {
          for (let i = 0; i < q.length; i++) {
            if (!ids.includes(q[i])) {
              dispatch("unqueue", { id: q[i] });
            }
          }
        }
        // queue new ids
        if (ids.length > 0) {
          let q = getters["getQueue"];
          for (let i = 0; i < ids.length; i++) {
            if (!q.includes(ids[i])) {
              dispatch("queue", { id: ids[i] }).then(() => {
                console.log(
                  `action: analyzers.sync -- callback ~ analyzers.queue (id=${ids[i]})`
                );
                dispatch("get_status", { id: ids[i] });
                dispatch("get_config", { id: ids[i] });
              });
            }
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
    console.log(`action: analyzers.get_config (id=${id})`);
    try {
      assert(!(id === undefined), "no id provided");

      return get_config(id).then(config => {
        console.log(
          `action: analyzers.get_config -- callback ~ api.get_config (id=${id})`
        );
        commit("setAnalyzerConfig", {
          id: id,
          config: config
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not get config for ${id}`);
      return undefined;
    }
  },

  async get_status({ commit }, { id }) {
    console.log(`action: analyzers.get_status (id=${id})`);
    try {
      assert(!(id === undefined), "no id provided");

      return get_status(id).then(status => {
        console.log(
          `action: analyzers.get_status -- callback ~ api.get_status (id=${id})`
        );
        commit("setAnalyzerStatus", { id: id, status: status });
      });
    } catch (e) {
      console.warn(`could not get status for ${id}`);
      return undefined;
    }
  },

  async set_config({ commit }, { id, config }) {
    console.log(`action: analyzers.set_config (id=${id})`);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(config === undefined), "no config");

      return set_config(id, config).then(config => {
        console.log(
          `action: analyzers.set_config -- callback ~ api.set_config (id=${id})`
        );
        commit("setAnalyzerConfig", {
          id: id,
          config: config
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not set config for ${id}`);
      return undefined;
    }
  }
};
