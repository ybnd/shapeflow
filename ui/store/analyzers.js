import Vue from "vue";
import axios from "axios";
import {
  AnalyzerState as ast,
  init,
  get_schemas,
  list,
  launch,
  get_config,
  set_config,
  analyze
} from "../assets/api";

export const state = () => ({
  options: {
    // arrays of available
    feature: [], // features to compute
    transform: [], // transform implementations
    filter: [] // filter implementations
  },
  analyzers: {
    // maps id to {state, config}
  },
  queue: [
    // ordered array of ids; dashboard & sidebar order, order of execution.
  ]
});

export const mutations = {
  addAnalyzer(state, id) {
    console.log(`addAnalyzer: ${id}`);
    state.analyzers = { ...state.analyzers, [id]: {} };
    console.log(state.analyzers);
  },

  queueAnalyzer(state, id) {
    console.log(`queueAnalyzer: ${id}`);
    state.queue = [...state.queue, id];
    console.log(state.queue);
  },

  setAnalyzerState(state, { id, analyzer_state }) {
    console.log(`setAnalyzerState: ${id}`);
    console.log(analyzer_state);
    if (state.analyzers[id] === undefined) {
      state.analyzers[id] = {};
    }
    state.analyzers[id].state = {
      ...state.analyzers[id],
      state: analyzer_state
    };
    console.log(state.analyzers);
  },

  setAnalyzerConfig(state, { id, analyzer_config }) {
    console.log(`setAnalyzerConfig: ${id}`);
    console.log(analyzer_config);
    if (state.analyzers[id] === undefined) {
      state.analyzers[id] = {};
    }
    state.analyzers[id] = {
      ...state.analyzers[id],
      config: analyzer_config
    };
    console.log(state.analyzers);
  },

  setAnalyzerSchemas(state, { id, analyzer_schemas }) {
    console.log(`setAnalyzerSchemas: ${id}`);
    console.log(analyzer_schemas);
    if (state.analyzers[id] === undefined) {
      state.analyzers[id] = {};
    }
    state.analyzers[id].schemas = {
      ...state.analyzers[id],
      config: analyzer_schemas
    };
    console.log(state.analyzers);
  },

  dropAnalyzer(state, id) {
    Vue.set(state, "queue", state.queue.splice(state.queue.indexOf(id, 1))); // todo: probably wrong
  }
};
export const getters = {
  getState: state => id => {
    return state.analyzers[id].state;
  },
  getConfig: state => id => {
    // return state.analyzers[id].config;
    return {};
  },
  getName: state => id => {
    // return state.analyzers[id].name;
    return id;
  },
  getIndex: state => id => {
    return state.queue.indexOf(id);
  }
};

export const actions = {
  init({ commit }) {
    console.log("Adding an analyzer...");
    init().then(id => {
      commit("addAnalyzer", id);
      commit("setAnalyzerState", { id: id, analyzer_state: ast.INCOMPLETE });
      get_schemas(id).then(schemas => {
        commit("setAnalyzerSchemas", { id: id, analyzer_schemas: schemas });
      });
      get_config(id).then(config => {
        commit("setAnalyzerConfig", { id: id, analyzer_config: config });
        // only queue AFTER config is committed
        commit("queueAnalyzer", id);
      });
    });
  },

  sync({ commit, state }) {
    list().then(data => {
      let ids = data.ids;
      let states = data.states;

      // remove dead ids from the queue
      if (state.queue.length > 0) {
        for (let i = 0; i < state.queue.length; i++) {
          // todo: can probably be replaced with a filter
          if (ids.includes(state.queue[i])) {
            // this id is still alive
          } else {
            commit("dropAnalyzer", { id: state.queue[i] });
          }
        }
      }

      // set id state
      if (ids.length > 0) {
        for (let i = 0; i < ids.length; i++) {
          if (!state.queue.includes(ids[i])) {
            // add new id to the queue
            commit("addAnalyzer", ids[i]);
            get_schemas(ids[i]).then(schemas => {
              commit("setAnalyzerSchemas", {
                id: ids[i],
                analyzer_schemas: schemas
              });
            });
            get_config(ids[i]).then(config => {
              commit("setAnalyzerConfig", { id: ids[i] }, config);
            });
            commit("setAnalyzerState", {
              id: ids[i],
              analyzer_state: states[i]
            });
            commit("queueAnalyzer", ids[i]);
          } else {
            commit("setAnalyzerState", {
              id: ids[i],
              analyzer_state: states[i]
            });
          }
        }
      }
    });
  }
};
