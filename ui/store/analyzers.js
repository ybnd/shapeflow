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
    /* maps id to
      {
        name,
        status,
        config,
        src: {
          status,
          config
        }
      }

    */
  };
};

export const mutations = {
  addAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      if (!(id in state)) {
        state = { ...state, [id]: {} };
      } else {
        console.warn(`addAnalyzerState: '${id}' already defined`);
      }
    } catch (err) {
      console.warn(`addAnalyzer failed: '${id}'`);
    }
  },

  setAnalyzerSources(state, { id, src }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(src === undefined), "no sources provided");
      assert("status" in src, "status EventSource not provided");
      assert("config" in src, "config EventSource not provided");

      state[id] = { ...state[id], src: src };
    } catch (err) {
      console.warn(`setAnalyzerSources failed: '${id}'`);
    }
  },

  setAnalyzerStatus(state, { id, analyzer_status: analyzer_status }) {
    console.log("analyzers/setAnalyzerStatus");
    console.log(id);
    console.log(analyzer_status);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_status === undefined), "no status");
      state[id] = { ...state[id], status: analyzer_status };
    } catch (err) {
      console.warn(
        `setAnalyzerStatus failed: '${id}', analyzer_status: ${analyzer_status}`
      );
    }
  },

  setAnalyzerConfig(state, { id, analyzer_config }) {
    console.log("analyzers/setAnalyserConfig");
    console.log(id);
    console.log(analyzer_config);
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_config === undefined), "no config");
      state[id] = { ...state[id], config: analyzer_config };

      if (!(analyzer_config.name === undefined)) {
        state[id].name = analyzer_config.name;
      } else {
        state[id].name = "!! unnamed !!";
        console.warn(`setAnalyzerConfig: using default name for '${id}'`);
      }
    } catch (err) {
      console.warn(
        `setAnalyzerConfig failed: '${id}', analyzer_config: ${analyzer_config}`
      );
    }
  },
  dropAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");

      state[id].src.status.close();
      state[id].src.config.close();
      delete state[id];
    } catch {
      `dropAnalyzer failed: '${id}'`;
    }
  }
};
export const getters = {
  getStatus: state => id => {
    if (id in state) {
      if ("status" in state[id]) {
        return state[id].status;
      }
    }
  },
  getConfig: state => id => {
    return state[id].config;
  },
  getFeatures: state => id => {
    return state[id].config.features;
  },
  getMasks: state => id => {
    return state[id].config.masks.map(({ name }) => name);
  },
  getFilterType: state => (id, mask_index) => {
    return state[id].config.masks[mask_index].filter.type;
  },
  getFilterData: state => (id, mask_index) => {
    return state[id].config.masks[mask_index].filter.data;
  },
  getRoi: state => id => {
    return state[id].config.transform.roi;
  },
  getName: state => id => {
    return state[id].name;
  },
  hasSources: state => id => {
    if (id in state) {
      if ("src" in state[id]) {
        return (
          state[id].src.status.readyState === 2 &&
          state[id].src.config.readyState === 2
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
  // todo: when running slowly (e.g. debugging), analyzers get duplicated
  async sources({ commit, getters }, { id }) {
    try {
      if (!getters["hasSources"](id)) {
        commit("setAnalyzerSources", {
          id: id,
          src: {
            status: stream(id, "stream-json/status", function(message) {
              console.log(`${id} status: ${message.data}`);
              commit("setAnalyzerStatus", {
                id: id,
                analyzer_status: JSON.parse(message.data)
              });
            }),
            config: stream(id, "stream-json/get_config", function(message) {
              console.log(`${id} config: ${message.data}`);
              commit("setAnalyzerConfig", {
                id: id,
                analyzer_config: JSON.parse(message.data)
              });
            })
          }
        });
      }
    } catch (err) {
      console.warn(err);
    }
    assert(!(id === undefined), "no id provided");
  },

  async init({ commit, dispatch }, { config = {} }) {
    return init().then(id => {
      commit("addAnalyzer", { id: id });
      dispatch("sources", { id: id });

      var config_promise;
      if (config === {}) {
        config_promise = get_config(id);
      } else {
        config_promise = set_config(id, config);
      }

      config_promise.then(config => {
        commit("setAnalyzerConfig", { id: id, analyzer_config: config });
        // get_schemas(id).then(schemas => {
        //   commit("setAnalyzerSchemas", { id: id, analyzer_schemas: schemas });
        // });
        launch(id).then(ok => {
          if (ok) {
            commit("queue/addToQueue", { id: id }, { root: true });
          } else {
            commit("dropAnalyzer", { id: id });
            console.warn(
              `Could not launch '${id}'; check the backend log for details.`
            );
          }
        });
      });
      return id;
    });
  },

  async sync({ commit, rootGetters }) {
    try {
      return await list().then(data => {
        let ids = data.ids; // todo: don't add state/progress to list
        let state = data.states;
        let progress = data.progress;

        // remove dead ids from the queue
        let q = rootGetters["queue/getQueue"];
        if (q.length > 0) {
          for (let i = 0; i < q.length; i++) {
            if (ids.includes(q[i])) {
              // this id is still alive
            } else {
              commit("queue/dropFromQueue", { id: q[i] }, { root: true });
              commit("dropAnalyzer", { id: q[i] });
            }
          }
        }

        // set id state
        if (ids.length > 0) {
          let q = rootGetters["queue/getQueue"];
          for (let i = 0; i < ids.length; i++) {
            if (!q.includes(ids[i])) {
              // add new id to the queue
              commit("addAnalyzer", { id: ids[i] });
              commit("queue/addToQueue", { id: ids[i] }, { root: true });
            }
            dispatch("sources", { id: ids[i] });
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
    // todo: should not be needed if streaming works
    try {
      assert(!(id === undefined), "no id provided");

      return await get_config(id).then(config => {
        commit("setAnalyzerConfig", {
          id: id,
          analyzer_config: config
        });
      });
    } catch (e) {
      console.warn(`could not get config for ${id}`);
      return false;
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
      return false;
    }
  }
};
