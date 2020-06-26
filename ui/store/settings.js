import Vue from "vue";
import { get_settings, set_settings, settings_schema } from "../static/api";

import assert from "assert";
import _ from "lodash";

export const state = () => {
  return {
    settings: undefined,
    schema: undefined,
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
  setSchema(state, { schema }) {
    try {
      assert(schema !== undefined);
      state.schema = schema;
    } catch (err) {
      console.warn(`settings.setSchema() failed`);
      console.warn(err);
    }
  },
};

export const getters = {
  getSettings: (state) => {
    return state.settings;
  },
  getSchema: (state) => {
    return state.schema;
  },
  isUndefined: (state) => {
    return state.settings === undefined && state.schema === undefined;
  },
};

export const actions = {
  async get({ commit, getters }) {
    return get_settings().then((settings) => {
      commit("setSettings", { settings: settings });
      return getters["getSettings"];
    });
  },
  async set({ commit, getters }, { settings = {} }) {
    return set_settings(settings).then((settings) => {
      commit("setSettings", { settings: settings });
      return getters["getSettings"];
    });
  },
  async schema({ commit, getters }) {
    return settings_schema().then((schema) => {
      commit("setSchema", { schema: schema });
      console.log("settings.schema() callback");
      return getters["getSchema"];
    });
  },
  async sync({ dispatch }) {
    return dispatch("get").then(() => {
      return dispatch("schema");
    });
  },
};
