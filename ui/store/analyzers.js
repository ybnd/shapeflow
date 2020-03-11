import Vue from "vue";
import axios from "axios";
import {
  analyzer_state as ast,
  init,
  get_schemas,
  list,
  launch,
  get_config,
  set_config
} from "../assets/api";

export const state = () => ({
  ids: [],
  analyzers: {
    // maps id to {state, config}
  },
  queue: [
    // ordered array of ids; dashboard & sidebar order, order of execution.
  ]
});

export const mutations = {
  init(state) {
    init().then(
      id => {
        get_schemas(id).then(
          schemas => {
            state.queue = [...state.queue, id];
            state.analyzers = {
              ...state.analyzers,
              [id]: { state: ast.INCOMPLETE, schemas: schemas }
            };
          },
          () => {
            state.queue = [...state.queue, id];
            state.analyzers = {
              ...state.analyzers,
              [id]: { state: ast.ERROR }
            };
          }
        );
      },
      () => {
        // do nothing.
      }
    );
  },

  list() {
    list().then(list => {
      // iterate over state.queue and remove anything's that's no longer there
    });
  },

  get_config(id) {
    get_config().then(
      config => {
        state.analyzers[id].config = config;
      },
      () => {
        state.analyzers[id].state = ast.ERROR;
      }
    );
  },

  set_config(id, config) {
    set_config(id, config).then(config => {});
  },

  launch(state, id) {
    launch().then(
      () => {
        state.analyzers[id].state = ast.LAUNCHED;
      },
      () => {
        state.analyzers[id].state = ast.ERROR;
      }
    );
  },

  analyze(state, id) {
    analyze().then(response => {
      if (response.staus === 200) {
        state.analyzers[id].state = ast.RUNNING;
      } else {
        state.analyzers[id].state = ast.ERROR;
      }
    });
  }
};

export const actions = {
  async newAnalyzer({ commit }) {
    commit("init");
  }
};
