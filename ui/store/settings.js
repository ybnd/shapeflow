import Vue from "vue";
import { get_settings, set_settings, settings_schema } from "../static/api";
import cloneDeep from "lodash/cloneDeep";

import assert from "assert";

export const state = () => {
  return {
    settings: undefined,
  };
};

export const mutations = {
  setSettings(state, { settings }) {
    try {
      assert(settings !== undefined);
      state.settings = settings;
    } catch (err) {
      console.warn(`settings.setSettings() failed`);
      console.warn(err);
    }
  },
};

export const getters = {
  getSettings: (state) => {
    return state.settings;
  },
  getSettingsCopy: (state) => {
    return cloneDeep(state.settings);
  },
  isUndefined: (state) => {
    return state.settings === undefined && state.schema === undefined;
  },
};

export const actions = {
  async get({ commit, getters }) {
    return get_settings().then((settings) => {
      commit("setSettings", { settings: settings });
      return getters["getSettingsCopy"];
    });
  },
  async set({ commit, getters }, { settings = {} }) {
    return set_settings(settings).then((settings) => {
      commit("setSettings", { settings: settings });
      return getters["getSettingsCopy"];
    });
  },
  async sync({ dispatch }) {
    return dispatch("get").then(() => {
      return true;
    });
  },
};
