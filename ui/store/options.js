import Vue from "vue";
import axios from "axios";
import { get_options, AnalyzerState } from "../static/api";
import assert from "assert";
import _ from "lodash";

export const state = () => ({
  analyzer: {},
  analyzer_state: AnalyzerState,
  feature: {
    options: [],
    labels: {},
    units: {},
    descriptions: {},
    parameters: {},
    parameter_defaults: {},
    parameter_descriptions: {}
  },
  frame_interval_setting: {
    options: [],
    descriptions: {}
  },
  transform: {
    options: [],
    descriptions: {}
  },
  filter: {
    options: [],
    descriptions: {}
  }
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
  setAnalyzerStateOptions(state, { options }) {
    try {
      assert(!(options === undefined), "no options provided");
      state.analyzer_state = options;
      // console.log(state);
    } catch (err) {
      console.warn(`setAnalyzerStateOptions failed`);
      console.warn(err);
    }
  },
  setFrameIntervalSettingOptions(state, { options }) {
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
  }
};

export const actions = {
  async sync({ commit }) {
    get_options("analyzer").then(options => {
      // console.log(options);
      commit("setAnalyzerOptions", { options: options });
    });
    get_options("state").then(options => {
      // console.log(options);
      commit("setAnalyzerStateOptions", { options: options });
      try {
        assert(
          _.isEqual(options, AnalyzerState),
          "AnalyzerState definition mismatch between frontend and backend"
        );
      } catch (e) {
        console.warn("backend AnalyzerState:");
        console.warn(options);
        console.warn("frontend AnalyzerState:");
        console.warn(AnalyzerState);
      }
    });
    get_options("frame_interval_setting").then(options => {
      // console.log(options);
      commit("setFrameIntervalSettingOptions", { options: options });
    });
    get_options("feature").then(options => {
      // console.log(options);
      commit("setFeatureOptions", { options: options });
    });
    get_options("transform").then(options => {
      // console.log(options);
      commit("setTransformOptions", { options: options });
    });
    get_options("filter").then(options => {
      // console.log(options);
      commit("setFilterOptions", { options: options });
    });
  }
};
