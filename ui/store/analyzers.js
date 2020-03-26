import Vue from "vue";
import {
  AnalyzerState as ast,
  get_config,
  set_config,
  get_schemas,
  init,
  list,
  launch
} from "../static/api";

export const state = () => ({
  // maps id to {name, state, config, coordinates, frame}
});

export const mutations = {
  addAnalyzer(state, id) {
    console.log(state);
    console.log("Adding analyzer");

    if (state[id] === undefined) {
      console.log(`${id} in state`);
    } else {
      console.log(`${id} not in state, apparently?`);
      state = { ...state, [id]: {} };
    }

    state[id] = { ...state[id], name: id.split("-")[0] }; // todo: placeholder for actual name
    console.log(state);
  },

  setAnalyzerState(state, { id, analyzer_state }) {
    if (state[id] === undefined) {
      state[id] = {};
    }
    if (analyzer_state === undefined) {
      analyzer_state = ast.UNKNOWN;
    }
    state[id] = { ...state[id], state: analyzer_state };
  },

  setAnalyzerConfig(state, { id, analyzer_config }) {
    if (state[id] === undefined) {
      state[id] = {};
    }
    state[id] = { ...state[id], config: analyzer_config };
  },

  setAnalyzerSchemas(state, { id, analyzer_schemas }) {
    if (state[id] === undefined) {
      state[id] = {};
    }
    state[id] = { ...state[id], schemas: analyzer_schemas };
  },

  dropAnalyzer(state, id) {
    delete state[id]; // todo: probably wrong
  }
};
export const getters = {
  getState: state => id => {
    return state[id].state;
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
  async init({ commit }) {
    return init().then(id => {
      commit("addAnalyzer", id);
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
      return id;
    });
  },

  async sync({ commit, rootGetters, dispatch }) {
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

      commit("queue/refresh", {}, { root: true });
    });
  }
};
