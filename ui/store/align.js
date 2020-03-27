import Vue from "vue";
import { getInitialTransform } from "../static/align";
import { get_relative_roi } from "../static/api";

export const state = () => {
  return {
    // maps id to {roi, frame, css_transform}
  };
};

export const mutations = {
  addAlign(state, { id }) {
    state[id] = {
      frame: null,
      initial_roi: null,
      initial_transform: null
    };
    console.log(state);
  },
  setFrame(state, { id, frame }) {
    console.log(state);

    if (!(state[id].frame === frame)) {
      let initial_transform = null;
      if (state[id].initial_roi) {
        initial_transform = getInitialTransform(state[id].initial_roi, frame);
      }
      state[id] = {
        ...state[id],
        frame: frame,
        initial_transform: initial_transform
      };
    }
    console.log(state);
  },
  setInitialRoi(state, { id, initial_roi }) {
    if (!(state[id].initial_roi === initial_roi)) {
      let initial_transform = null;
      if (state[id].frame) {
        initial_transform = getInitialTransform(initial_roi, state[id].frame);
      }
      state[id] = {
        ...state[id],
        initial_roi: initial_roi,
        initial_transform: initial_transform
      };
      console.log(state);
    }
  }
  // Assume that it's not necessary to remove entries from this store
  // May cause if the application runs for a long time without refreshing / reloading,
  //  but is also easily solved by just refreshing, so it's not a priority
};

export const getters = {
  getFrame: state => id => {
    return state[id].frame;
  },
  getInitialRoi: state => id => {
    return state[id].initial_roi;
  },
  getInitialTransform: state => id => {
    return state[id].initial_transform;
  }
};

export const actions = {
  async init({ commit }, { id }) {
    commit("addAlign", { id: id });

    return get_relative_roi(id).then(roi => {
      commit("setInitialRoi", { id: id, initial_roi: roi });
    });
  },
  async getRoi({ commit }, { id }) {
    return get_relative_roi(id).then(roi => {
      commit("setInitialRoi", { id: id, initial_roi: roi });
    });
  }
};
