import Vue from 'vue'
import axios from 'axios'
import { analyzer_state as ast, init, get_schemas, list, launch, get_config, set_config } from '../assets/api'

export const state = () => ({
  ids: [],
  analyzers: {  // maps id to {state, config}

  },
  queue: [      // ordered array of ids; dashboard & sidebar order, order of execution.

  ],

});

export const mutations = {
  async init (state) {
    init().then(
      (id) => {
        get_schemas(id).then(
          (schemas) => {
            state.queue = [ ...state.queue, id];
            state.analyzers = {
              ...state.analyzers,
              [id]: {state: ast.INCOMPLETE, schemas: schemas,}
            };
          },
          () => {
            state.queue = [ ...state.queue, id];
            state.analyzers = {
              ...state.analyzers,
              [id]: {state: ast.ERROR}
            };
          }
        )
      },
      () => {
        // do nothing.
      }
    );
  },
  async list () {
    list().then(
      (list) => {

      },

    )
  },

  async launch (state, id) {
    launch().then(
      (ok) => {
        if (ok) {
          state.analyzers[id].state = ast.LAUNCHED;
        } else {
          state.analyzers[id].state = ast.ERROR;
        }
      }
    )
  },
};

export const actions = {
  async newAnalyzer({commit}) {
    commit('init');
  },
};
