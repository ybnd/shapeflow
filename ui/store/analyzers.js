import Vue from "vue";
import {
  AnalyzerState as ast,
  get_config,
  set_config,
  get_state,
  get_schemas,
  init,
  list,
  launch
} from "../static/api";

import assert from "assert";

export const state = () => {
  return {
    // maps id to {name, state, progress, config}
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

  setAnalyzerState(state, { id, analyzer_state }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_state === undefined), "no state");
      state[id] = { ...state[id], state: analyzer_state };
    } catch (err) {
      console.warn(
        `setAnalyzerState failed: '${id}', analyzer_state: ${analyzer_state}`
      );
    }
  },

  setAnalyzerProgress(state, { id, analyzer_progress }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_progress === undefined), "no progress");
      state[id] = { ...state[id], progress: analyzer_progress };
    } catch (err) {
      console.warn(
        `setAnalyzerProgress failed: '${id}', analyzer_progress: ${analyzer_progress}`
      );
    }
  },

  setAnalyzerConfig(state, { id, analyzer_config }) {
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

  setAnalyzerSchemas(state, { id, analyzer_schemas }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(analyzer_schemas === undefined), "no schemas");
      state[id] = { ...state[id], schemas: analyzer_schemas };
    } catch (err) {
      console.warn(
        `setAnalyzerSchemas failed: '${id}', analyzer_schemas: ${analyzer_schemas}`
      );
    }
  },
  dropAnalyzer(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      delete state[id];
    } catch {
      `dropAnalyzer failed: '${id}'`;
    }
  }
};
export const getters = {
  getState: state => id => {
    return state[id].state;
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
  }
};

export const actions = {
  // todo: when running slowly (e.g. debugging), analyzers get duplicated
  async init({ commit }, { config = {} }) {
    return init().then(id => {
      commit("addAnalyzer", { id: id });

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
            get_state(id).then(state => {
              commit("setAnalyzerState", { id: id, analyzer_state: state });
              commit("queue/addToQueue", { id: id }, { root: true });
            });
          } else {
            commit("dropAnalyzer", { id: id });
            console.warn(
              `Could not launch '${id}'; check the backend logs for details.`
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
        let ids = data.ids;
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
              // get_schemas(ids[i]).then(schemas => {
              //   commit("setAnalyzerSchemas", {
              //     id: ids[i],
              //     analyzer_schemas: schemas
              //   });
              // });
              get_config(ids[i]).then(config => {
                commit("setAnalyzerState", {
                  id: ids[i],
                  analyzer_state: state[i]
                });
                commit("setAnalyzerProgress", {
                  id: ids[i],
                  analyzer_state: progress[i]
                });
                commit("setAnalyzerConfig", {
                  id: ids[i],
                  analyzer_config: config
                });
                commit("queue/addToQueue", { id: ids[i] }, { root: true });
              });
            } else {
              commit("setAnalyzerState", {
                id: ids[i],
                analyzer_state: state[i]
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
