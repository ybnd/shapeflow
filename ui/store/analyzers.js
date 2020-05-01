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
  stream,
  get_status
} from "../static/api";

import assert from "assert";

export const state = () => {
  return {
    queue: [],
    status: {},
    config: {},
    source: {}
  };
};

export const mutations = {
  addAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      if (!(id in state)) {
        state.status = { ...state.config, [id]: {} };
        state.config = { ...state.status, [id]: {} };
        state.source = { ...state.source, [id]: {} };
      } else {
        console.warn(`addAnalyzerState: '${id}' already defined`);
      }
    } catch (err) {
      console.warn(`addAnalyzer failed: '${id}'`);
      console.warn(err);
    }
  },

  setAnalyzerSources(state, { id, src }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(src === undefined), "no sources provided");
      assert("status" in src, "status EventSource not provided");
      assert("config" in src, "config EventSource not provided");

      state.source[id] = {
        ...state.source[id],
        ...src
      };
    } catch (err) {
      console.warn(`setAnalyzerSources failed: '${id}'`);
      console.warn(err);
    }
  },

  setAnalyzerStatus(state, { id, analyzer_status: analyzer_status }) {
    // console.log("analyzers/setAnalyzerStatus");
    // console.log(id);
    // console.log(analyzer_status);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_status === undefined), "no status");

      state.status[id] = {
        ...state.status[id],
        ...analyzer_status
      };
    } catch (err) {
      console.warn(`setAnalyzerStatus failed: '${id}', analyzer_status: `);
      console.warn(analyzer_status);
      console.warn(err);
    }
  },

  setAnalyzerConfig(state, { id, analyzer_config }) {
    // console.log("analyzers/setAnalyserConfig");
    // console.log(id);
    // console.log(analyzer_config);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_config === undefined), "no config");

      state.config[id] = {
        ...state.config[id],
        ...analyzer_config
      };

      if (!(analyzer_config.name === undefined)) {
        state.config[id].name = analyzer_config.name;
      } else {
        state.config[id].name = "!! unnamed !!";
        console.warn(`setAnalyzerConfig: using default name for '${id}'`);
      }
    } catch (err) {
      console.warn(`setAnalyzerConfig failed: '${id}', analyzer_config: `);
      console.warn(analyzer_config);
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
  }
};
export const getters = {
  getFullStatus: state => {
    return state.status;
  },
  getStatus: state => id => {
    if (id in state) {
      if ("status" in state[id]) {
        return state[id].status;
      }
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
  getFilterType: state => (id, mask_index) => {
    return state.config[id].masks[mask_index].filter.type;
  },
  getFilterData: state => (id, mask_index) => {
    return state.config[id].masks[mask_index].filter.data;
  },
  getRoi: state => id => {
    return state.config[id].transform.roi;
  },
  getName: state => id => {
    return state.config[id].name;
  },
  hasSources: state => id => {
    if (id in state) {
      if ("src" in state[id]) {
        return (
          state.source[id].status.readyState === 2 &&
          state.source[id].config.readyState === 2
        );
      } else {
        return false;
      }
    } else {
      return false;
    }
  }
};

export const actions = {
  async sources({ commit, getters }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      if (!getters["hasSources"](id)) {
        commit("setAnalyzerSources", {
          id: id,
          src: {
            status: stream(id, "stream-json/status", function(message) {
              // console.log(`${id} status:`);
              let status = JSON.parse(message.data);
              // console.log(status);

              commit("setAnalyzerStatus", {
                id: id,
                analyzer_status: status
              });
            }),
            config: stream(id, "stream-json/get_config", function(message) {
              // console.log(`${id} config:`);
              let config = JSON.parse(message.data);
              // console.log(config);

              commit("setAnalyzerConfig", {
                id: id,
                analyzer_config: config
              });
            })
          }
        });
      }
    } catch (err) {
      console.warn(err);
    }
  },

  async queue({ commit, dispatch }, { id }) {
    commit("addAnalyzer", { id: id });
    return dispatch("sources", { id: id }).then(() => {
      commit("queue/addToQueue", { id: id }, { root: true });
    });
  },

  async unqueue({ commit }, { id }) {
    commit("queue/dropFromQueue", { id: id }, { root: true });
    commit("dropAnalyzer", { id: id });
  },

  async init({ commit, dispatch }, { config = {} }) {
    return init().then(id => {
      dispatch("queue", { id: id }).then(() => {
        dispatch("set_config", { id: id, config: config }).then(() => {
          launch(id).then(ok => {
            if (ok) {
              console.log(`Launched '${id}'`);
            } else {
              dispatch("unqueue", { id: id });
              console.warn(`Could not launch '${id}'`);
            }
          });
        });
      });
      return id;
    });
  },

  async sync({ commit, dispatch, rootGetters }) {
    try {
      return await list().then(ids => {
        // unqueue dead ids
        let q = rootGetters["queue/getQueue"];
        if (q.length > 0) {
          for (let i = 0; i < q.length; i++) {
            if (!ids.includes(q[i])) {
              dispatch("unqueue", { id: q[i] });
            }
          }
        }
        // queue new ids
        if (ids.length > 0) {
          let q = rootGetters["queue/getQueue"];
          for (let i = 0; i < ids.length; i++) {
            if (!q.includes(ids[i])) {
              dispatch("queue", { id: ids[i] }).then(() => {
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
    try {
      assert(!(id === undefined), "no id provided");

      return get_config(id).then(config => {
        commit("setAnalyzerConfig", {
          id: id,
          analyzer_config: config
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not get config for ${id}`);
      return undefined;
    }
  },

  async get_status({ commit }, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      return get_status(id).then(status => {
        commit("setAnalyzerStatus", { id: id, analyzer_status: status });
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

      return await set_config(id, config).then(config => {
        commit("setAnalyzerConfig", {
          id: id,
          analyzer_config: config
        });
        return config;
      });
    } catch (e) {
      console.warn(`could not set config for ${id}`);
      return undefined;
    }
  }
};
