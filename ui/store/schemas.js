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
    parameter_defaults: {},
    parameter_descriptions: {},
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
    // AnalyzerConfig schema  todo: this also makes more sense for filter/transform/feature
  },
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
    // console.log("schemas/setTransformOptions");
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

      state.feature = {
        options: schema.properties.features.items.enum,
        descriptions: schema.properties.features.items.descriptions,
        labels: schema.properties.features.items.labels,
        units: schema.properties.features.items.units,
        parameters: schema.properties.features.items.enum.map((v) =>
          Object.keys(
            schema.implementations[schema.properties.features.items.interface][
              v
            ].properties
          )
        ),
        parameter_defaults: schema.properties.features.items.enum.reduce(
          // todo: way too convoluted, refactor BasicConfig!
          function (o, v) {
            return {
              ...o,
              [v]: Object.keys(
                schema.implementations[
                  schema.properties.features.items.interface
                ][v].properties
              ).reduce(function (p, w) {
                return {
                  ...p,
                  [w]:
                    schema.implementations[
                      schema.properties.features.items.interface
                    ][v].properties[w].default,
                };
              }, {}),
            };
          },
          {}
        ),
        parameter_descriptions: schema.properties.features.items.enum.reduce(
          // todo: way too convoluted, refactor BasicConfig!
          function (o, v) {
            return {
              ...o,
              [v]: Object.keys(
                schema.implementations[
                  schema.properties.features.items.interface
                ][v].properties
              ).reduce(function (p, w) {
                return {
                  ...p,
                  [w]:
                    schema.implementations[
                      schema.properties.features.items.interface
                    ][v].properties[w].description,
                };
              }, {}),
            };
          },
          {}
        ),
      };

      const transform_schema = dereference(
        schema,
        get_reference(schema.properties.transform)
      );
      state.transform = {
        options: transform_schema.properties.type.enum,
        descriptions: transform_schema.properties.type.enum.map(
          (v) =>
            schema.implementations[transform_schema.properties.type.interface][
              v
            ].description
        ),
      };

      const filter_schema = dereference(
        schema,
        get_reference(
          dereference(schema, get_reference(schema.properties.masks)).properties
            .filter
        )
      );
      state.filter = {
        options: filter_schema.properties.type.enum,
        descriptions: filter_schema.properties.type.enum.map(
          (v) =>
            schema.implementations[filter_schema.properties.type.interface][v]
              .description
        ),
      };
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
  getTransformOptions: (state) => {
    return state.transform;
  },
  getFilterOptions: (state) => {
    return state.filter;
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
