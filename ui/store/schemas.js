import Vue from "vue";
import axios from "axios";
import { AnalyzerState, get_schemas } from "../static/api";
import assert from "assert";

import { get_reference, dereference } from "static/util";

import isEmpty from "lodash/isEmpty";
import isEqual from "lodash/isEqual";

export const state = () => ({
  analyzer_state: {
    options: AnalyzerState,
    match: null,
  },
  frame_interval_setting: {
    options: [],
    descriptions: {},
  },
  feature: {
    options: [],
    labels: {},
    units: {},
    descriptions: {},
    parameters: {},
    defaults: {},
  },
  config: undefined,
  settings: undefined,
});

export const mutations = {
  setAnalyzerOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.analyzer = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setAnalyzerOptions failed`);
      console.warn(err);
    }
  },
  setAnalyzerStateMatch(state, { match }) {
    try {
      assert(!(match === undefined), "no match Boolean provided");
      state.analyzer_state.match = match;
      // console.log(state);
    } catch (err) {
      console.warn(`setAnalyzerStateMatch failed`);
      console.warn(err);
    }
  },
  setSettingsSchema(state, { schema }) {
    try {
      assert(!(schema === undefined), "no schema provided");
      state.settings = schema;
    } catch (err) {
      console.warn(`setSettingsSchema failed`);
      console.warn("schema=");
      console.warn(schema);
      console.warn(err);
    }
  },
  setConfigSchema(state, { schema }) {
    try {
      assert(!(schema === undefined), "no schema provided");
      state.config = schema;

      state.frame_interval_setting = {
        options: schema.properties.frame_interval_setting.enum,
        descriptions: schema.properties.frame_interval_setting.descriptions,
      };

      const features = schema.properties.features.items.enum;
      const implementations =
        schema.implementations[schema.properties.features.items.interface];

      state.feature = {
        options: features,
        descriptions: schema.properties.features.items.descriptions,
        labels: schema.properties.features.items.labels,
        units: schema.properties.features.items.units,

        parameters: features.reduce(function (o, v) {
          return {
            ...o,
            [v]: implementations[v].properties,
          };
        }, {}),

        defaults: features.reduce(function (o, v) {
          const props = Object.keys(implementations[v].properties);
          return {
            ...o,
            [v]: props.reduce(function (p, w) {
              return {
                ...p,
                [w]: implementations[v].properties[w].default,
              };
            }, {}),
          };
        }, {}),
      };

      // console.log(state);
    } catch (err) {
      console.warn(`setConfigSchema failed`);
      console.warn("schema=");
      console.warn(schema);
      console.warn(err);
    }
  },
};

export const getters = {
  isNotInitialized: (state) => {
    return isEmpty(state.config); // todo: more checks?
  },
  getConfigSchema: (state) => {
    return state.config;
  },
  getSettingsSchema: (state) => {
    return state.settings;
  },
  getFeature: (state) => {
    return state.feature;
  },
  getFrameIntervalSetting: (state) => {
    return state.frame_interval_setting;
  },
};

export const actions = {
  async sync({ commit, getters }) {
    if (getters["isNotInitialized"]) {
      get_schemas().then((schemas) => {
        commit("setConfigSchema", { schema: schemas.config });
        commit("setSettingsSchema", { schema: schemas.settings });
        // todo: include sanity checks
      });
    }
  },
};
