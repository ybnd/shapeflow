import {mutations, getters, actions, state} from '../schemas'
import { api } from '../../src/api'

import {startServer, killServer} from "../../src/shapeflow";

import {test, describe, beforeEach, afterEach, beforeAll, afterAll} from "@jest/globals";

import {createLocalVue} from "@vue/test-utils";
import Vuex from 'vuex';
import {retryOnce} from "../../src/util";

var SCHEMAS = undefined;

beforeAll(async () => {
  startServer();
  SCHEMAS = await retryOnce(api.schemas);
});

afterAll(() => {
  killServer();
});

test('state', () => {
  state()
})

describe('mutations & getters', () => {
  test('setSettingsSchema', () => {
    const s = state();

    mutations.setSettingsSchema(s, {schema: SCHEMAS.settings})
    expect(s.settings).toStrictEqual(SCHEMAS.settings)
  })

  test('setSettingsSchema -> undefined', () => {
    const s = state();

    mutations.setSettingsSchema(s, {schema: SCHEMAS.settings})
    expect(s.settings).toStrictEqual(SCHEMAS.settings)
    mutations.setSettingsSchema(s, {schema: undefined})
    expect(s.settings).toStrictEqual(SCHEMAS.settings)
  })

  test('setConfigSchema', () => {
    const s = state();

    mutations.setConfigSchema(s, {schema: SCHEMAS.config})
    expect(s.config).toStrictEqual(SCHEMAS.config)

    // check parsing of frame_interval_setting
    expect(s.frame_interval_setting.options).toStrictEqual(['Nf', 'dt']);
    expect(s.frame_interval_setting.descriptions).toHaveProperty('Nf');
    expect(s.frame_interval_setting.descriptions).toHaveProperty('dt');

    // check parsing of feature
    const FEATURES = Object.keys(SCHEMAS.config['implementations']['FeatureConfig']);

    expect(s.feature.options).toHaveLength(FEATURES.length);
    expect(s.feature.default).not.toBe('');

    for (var f of FEATURES) {
      expect(s.feature.labels).toHaveProperty(f);
      expect(s.feature.units).toHaveProperty(f);
      expect(s.feature.descriptions).toHaveProperty(f);
      expect(s.feature.parameters).toHaveProperty(f);
      expect(s.feature.defaults).toHaveProperty(f);
    }
  })

  test('setConfigSchema -> undefined', () => {
    const s = state();

    mutations.setConfigSchema(s, {schema: undefined})
    expect(s.config).not.toStrictEqual(SCHEMAS.config)

    // check parsing of frame_interval_setting
    expect(s.frame_interval_setting.options).toHaveLength(0);
    expect(s.frame_interval_setting.descriptions).not.toHaveProperty('Nf');
    expect(s.frame_interval_setting.descriptions).not.toHaveProperty('dt');

    expect(s.feature.options).toHaveLength(0);
    expect(s.feature.default).toBe('');

    expect(s.feature.labels).toStrictEqual({});
    expect(s.feature.units).toStrictEqual({});
    expect(s.feature.descriptions).toStrictEqual({});
    expect(s.feature.parameters).toStrictEqual({});
    expect(s.feature.defaults).toStrictEqual({});
  })

  test('isNotInitialized', () => {
    const s = state();

    expect(getters.isNotInitialized(s)).toBe(true);
    mutations.setConfigSchema(s, {schema: SCHEMAS.config})
    expect(getters.isNotInitialized(s)).toBe(false);
  })

  test('getConfigSchema', () => {
    const s = state();

    expect(getters.getConfigSchema(s)).not.toStrictEqual(SCHEMAS.config)
    mutations.setConfigSchema(s, {schema: SCHEMAS.config})
    expect(getters.getConfigSchema(s)).toStrictEqual(SCHEMAS.config)
  })

  test('getSettingsSchema', () => {
    const s = state();

    expect(getters.getSettingsSchema(s)).not.toStrictEqual(SCHEMAS.settings)
    mutations.setSettingsSchema(s, {schema: SCHEMAS.settings})
    expect(getters.getSettingsSchema(s)).toStrictEqual(SCHEMAS.settings)
  })

  test('getFeature', () => {
    const s = state();

    const f = getters.getFeature(s)
    expect(f).toHaveProperty('options')
    expect(f).toHaveProperty('default')
    expect(f).toHaveProperty('labels')
    expect(f).toHaveProperty('units')
    expect(f).toHaveProperty('descriptions')
    expect(f).toHaveProperty('parameters')
    expect(f).toHaveProperty('defaults')
  })

  test('getFrameIntervalSetting', () => {
    const s = state();

    const fis = getters.getFrameIntervalSetting(s);
    expect(fis).toHaveProperty('options')
    expect(fis).toHaveProperty('descriptions')
  })
})

describe('actions', () => {
  var localVue = undefined;
  var store = undefined;

  beforeEach(() => {
    localVue = createLocalVue();
    localVue.use(Vuex)
    store = new Vuex.Store({
      state: { settings: {} },
      mutations: mutations,
      getters: getters,
      actions: actions,
    })

    const end = Date.now() + 1000;
    while (Date.now() < end) {}
  })

  afterEach(() => {
    store = undefined;
  })

  test('sync', done => {
    store.dispatch('sync').then(() => {
      expect(store.getters.getSettingsSchema).toStrictEqual(SCHEMAS.settings);
      expect(store.getters.getConfigSchema).toStrictEqual(SCHEMAS.config);
      done();
    })
  })
})
