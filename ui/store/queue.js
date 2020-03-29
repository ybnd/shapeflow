import Vue from "vue";
import assert from "assert";

export const state = () => ({
  queue: [
    // ordered array of ids; dashboard & sidebar order, order of execution.
  ]
});

export const mutations = {
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
  }
};
