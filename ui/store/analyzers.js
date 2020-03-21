import Vue from "vue";
import {
  AnalyzerState as ast,
  get_config,
  get_schemas,
  init,
  list
} from "../assets/api";

export const state = () => ({
  analyzers: {
    // maps id to {state, config}
  }
});

export const mutations = {
  addAnalyzer(state, id) {
    console.log(`addAnalyzer: ${id}`);
    state.analyzers = { ...state.analyzers, [id]: { name: id.split("-")[0] } };
    console.log(state.analyzers);
  },

  setAnalyzerState(state, { id, analyzer_state }) {
    console.log(`setAnalyzerState: ${id}`);
    console.log(analyzer_state);
    if (state.analyzers[id] === undefined) {
      state.analyzers[id] = {};
    }
    if (analyzer_state === undefined) {
      analyzer_state = ast.UNKNOWN;
    }
    state.analyzers[id].state = analyzer_state;
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
    state.analyzers[id].schemas = analyzer_schemas;
    console.log(state.analyzers);
  },

  dropAnalyzer(state, id) {
    delete state.analyzers[id]; // todo: probably wrong
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
    console.log("Adding an roi...");
    init().then(id => {
      commit("addAnalyzer", id);
      commit("setAnalyzerState", {
        id: id,
        analyzer_state: ast.NOT_READY
      });
      // get_schemas(id).then(schemas => {
      //   commit("setAnalyzerSchemas", {
      //     id: id,
      //     analyzer_schemas: schemas
      //   });
      // });
      get_config(id).then(config => {
        commit("setAnalyzerConfig", {
          id: id,
          analyzer_config: config
        });
        // only queue AFTER config is committed
        commit("queue/queueAnalyzer", { id: id }, { root: true });
      });
    });
  },

  async sync({ commit, rootGetters }) {
    await list().then(data => {
      let ids = data.ids;
      let states = data.states;

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
            commit("addAnalyzer", ids[i]);
            // get_schemas(ids[i]).then(schemas => {
            //   commit("setAnalyzerSchemas", {
            //     id: ids[i],
            //     analyzer_schemas: schemas
            //   });
            // });
            get_config(ids[i]).then(config => {
              commit("setAnalyzerConfig", {
                id: ids[i],
                analyzer_config: config
              });
              commit("setAnalyzerState", {
                id: ids[i],
                analyzer_state: states[i]
              });
              commit("queue/addToQueue", { id: ids[i] }, { root: true });
            });
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
