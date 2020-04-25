import Vue from "vue";
import {
  getInitialTransform,
  roiIsValid,
  default_relative_coords,
  roiRectInfoToRelativeCoordinates,
  getDefaultRoi
} from "../static/coordinates";
import { get_relative_roi, init } from "../static/api";
import assert from "assert";

export const state = () => {
  return {
    // maps id to {frame, initial_roi, initial_transform}
  };
};

export const mutations = {
  addAlign(state, { id }) {
    try {
      assert(!(id === undefined), "no id provided");
      state[id] = {
        frame: null,
        initial_roi: null,
        initial_transform: null,
        overlay: null
      };
      if (!(id in state)) {
        state = { ...state, [id]: {} };
      } else {
        console.warn(`addAlign: '${id}' already defined`);
      }
    } catch (err) {
      console.warn(`addAlign failed: '${id}'`);
    }
  },
  setFrame(state, { id, frame }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(frame === undefined), "no frame");
      if (!(state[id].frame === frame)) {
        let initial_transform = null;
        if (state[id].initial_roi && state[id].overlay) {
          initial_transform = getInitialTransform(
            state[id].initial_roi,
            frame,
            state[id].overlay
          );
        }
        state[id] = {
          ...state[id],
          frame: frame,
          initial_transform: initial_transform
        };
      }
    } catch (err) {
      console.warn(`setFrame failed: '${id}', frame: ${frame}`);
    }
  },
  setOverlay(state, { id, overlay }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(overlay === undefined), "no overlay");
      if (!(state[id].overlay === overlay)) {
        let initial_transform = null;
        if (state[id].initial_roi && state[id].frame) {
          initial_transform = getInitialTransform(
            state[id].initial_roi,
            state[id].frame,
            overlay
          );
        }
        state[id] = {
          ...state[id],
          overlay: overlay,
          initial_transform: initial_transform
        };
      }
    } catch (err) {
      console.warn(`setOverlay failed: '${id}', overlay: ${overlay}`);
    }
  },
  setInitialRoi(state, { id, initial_roi }) {
    try {
      assert(!(id === undefined), "no id provided");
      assert(!(initial_roi === undefined), "no initial_roi");
      if (!(state[id].initial_roi === initial_roi)) {
        let initial_transform = null;
        if (state[id].frame && state[id].overlay) {
          initial_transform = getInitialTransform(
            initial_roi,
            state[id].frame,
            state[id].overlay
          );
        }
        state[id] = {
          ...state[id],
          initial_roi: initial_roi,
          initial_transform: initial_transform
        };
      }
    } catch (err) {
      console.warn(
        `setInitialRoi failed: '${id}', initial_roi: ${initial_roi}`
      );
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
  async init({ commit, dispatch }, { id }) {
    commit("addAlign", { id: id });
    dispatch("getRoi", { id: id });
  },
  async getRoi({ commit, getters }, { id }) {
    return get_relative_roi(id).then(roi => {
      if (!roiIsValid(roi)) {
        roi = default_relative_coords;
      }

      commit("setInitialRoi", { id: id, initial_roi: roi });
    });
  }
};
