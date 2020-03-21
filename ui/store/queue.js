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
  queue: [
    // ordered array of ids; dashboard & sidebar order, order of execution.
  ]
});

export const mutations = {
  addToQueue(state, { id }) {
    console.log(`addToQueue: ${id}`);
    state.queue = [...state.queue, id];
    console.log(state.queue);
  },
  dropFromQueue(state, { id }) {
    Vue.set(state, "queue", state.queue.splice(state.queue.indexOf(id, 1))); // todo: probably wrong
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
    return state.queue;
  },
  getIndex: state => id => {
    return state.queue.indexOf(id);
  }
};

export const actions = {
  refresh({ state, commit }) {
    let temp_queue = state.queue;
    console.log(temp_queue);
    console.log("Clearing queue...");
    commit("clearQueue");
    console.log("Restoring queue...");
    console.log(temp_queue);
    commit("setQueue", { queue: temp_queue });
  }
};
