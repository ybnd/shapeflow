import Vue from "vue";
import axios from "axios";
import { get_options, AnalyzerState } from "../static/api";
import assert from "assert";
import _ from "lodash";

export const state = () => ({
  analyzer: [], // todo: can be merged with config à la rest of things
  analyzer_state: {
    options: AnalyzerState,
    match: null,
  },
  feature: {
    options: [],
    labels: {},
    units: {},
    descriptions: {},
    parameters: {},
    parameter_defaults: {},
    parameter_descriptions: {},
  },
  frame_interval_setting: {
    options: [],
    descriptions: {},
  },
  transform: {
    options: [],
    descriptions: {},
    // todo: add schemas for TransformConfig
  },
  filter: {
    options: [],
    descriptions: {},
    // todo: add schemas for FilterConfig
  },
  config: {
    // AnalyzerType: AnalyzerConfig schema  todo: this also makes more sense for filter/transform/feature
  },
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
  setFrameIntervalSettingOptions(state, { options: options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.frame_interval_setting = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setFrameIntervalSettingOptions failed`);
      console.warn(err);
    }
  },
  setFeatureOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.feature = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setFeatureOptions failed`);
      console.warn(err);
    }
  },
  setTransformOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.transform = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setTransformOptions failed`);
      console.warn(err);
    }
  },
  setFilterOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.filter = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setFilterOptions failed`);
      console.warn(err);
    }
  },
  setConfigOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.config = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setConfigOptions failed`);
      console.warn(err);
    }
  },
};

export const getters = {
  hasNoAnalyzerOptions: (state) => {
    return _.isEmpty(state.analyzer);
  },
  hasNoAnalyzerStateMatch: (state) => {
    return state.analyzer_state.match === null;
  },
  hasNoFrameIntervalSettingOptions: (state) => {
    return _.isEmpty(state.frame_interval_setting.options);
  },
  hasNoFeatureOptions: (state) => {
    return _.isEmpty(state.feature.options);
  },
  hasNoTransformOptions: (state) => {
    return _.isEmpty(state.transform.options);
  },
  hasNoFilterOptions: (state) => {
    return _.isEmpty(state.filter.options);
  },
  hasNoConfigSchemas: (state) => {
    return _.isEmpty(state.config);
  },
  getConfigSchema: (state) => {
    return state.config;
  },
};

export const actions = {
  async sync({ commit, getters }) {
    if (getters["hasNoAnalyzerOptions"]) {
      get_options("analyzer").then((options) => {
        // console.log(options);
        commit("setAnalyzerOptions", { options: options });
      });
    }

    if (getters["hasNoAnalyzerStateMatch"]) {
      get_options("state").then((options) => {
        try {
          assert(
            _.isEqual(options, AnalyzerState),
            "AnalyzerState definition mismatch between frontend and backend"
          );
          commit("setAnalyzerStateMatch", { match: true });
        } catch (e) {
          console.warn("backend AnalyzerState:");
          console.warn(options);
          console.warn("frontend AnalyzerState:");
          console.warn(AnalyzerState);
          commit("setAnalyzerStateMatch", { match: false });
        }
      });
    }

    if (getters["hasNoFrameIntervalSettingOptions"]) {
      get_options("frame_interval_setting").then((options) => {
        // console.log(options);
        commit("setFrameIntervalSettingOptions", { options: options });
      });
    }

    if (getters["hasNoFeatureOptions"]) {
      get_options("feature").then((options) => {
        // console.log(options);
        commit("setFeatureOptions", { options: options });
      });
    }

    if (getters["hasNoTransformOptions"]) {
      get_options("transform").then((options) => {
        // console.log(options);
        commit("setTransformOptions", { options: options });
      });
    }

    if (getters["hasNoFilterOptions"]) {
      get_options("filter").then((options) => {
        // console.log(options);
        commit("setFilterOptions", { options: options });
      });
    }

    if (getters["hasNoConfigSchemas"]) {
      get_options("config").then((options) => {
        // console.log(options);
        commit("setConfigOptions", { options: options });
      });
    }
  },
};
