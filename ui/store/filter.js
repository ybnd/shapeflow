import Vue from "vue";
import { clickEventToRelativeCoordinate } from "../static/coordinates";
import { set_filter } from "../static/api";
import assert from "assert";

export const state = () => {
  return {
    // maps id to {frame}
  };
};

export const mutations = {
  addFilter(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      state[id] = {
        frame: null
      };
      if (!(id in state)) {
        state = { ...state, [id]: {} };
      } else {
        console.warn(`addFilter: '${id}' already defined`);
      }
    } catch (err) {
      console.warn(`addFilter failed: '${id}'`);
    }
  },
  setFrame(state, { id, frame }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(frame === undefined), "no frame");
      if (!(state[id].frame === frame)) {
        state[id] = {
          ...state[id],
          frame: frame
        };
      }
    } catch (err) {
      console.warn(`setFrame failed: '${id}', frame: ${frame}`);
    }
  }
  // Assume that it's not necessary to remove entries from this store
  // May cause if the application runs for a long time without refreshing / reloading,
  //  but is also easily solved by just refreshing, so it's not a priority
};

export const getters = {
  getFrame: state => id => {
    console.log("trying to get frame");
    console.log(state);
    return state[id].frame;
  }
};

export const actions = {
  async init({ commit }, { id }) {
    commit("addFilter", { id: id });
  },
  set({ commit, getters }, { id, event }) {
    let frame = getters.getFrame(id);
    if (frame !== null) {
      set_filter(id, clickEventToRelativeCoordinate(event, frame));
    }
  }
};
