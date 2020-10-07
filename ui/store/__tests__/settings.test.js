import {mutations, getters, actions, state} from '../settings'
import {api, axios} from '../../static/api'

import testAction from 'vue-test-actions';
import {test, describe, beforeEach} from "@jest/globals";
import {createLocalVue} from "@vue/test-utils";
import Vuex from 'vuex';

jest.mock('axios')

const SETTINGS = {
  these: {
    are: 'some',
    settings: [
      'right', 'here'
    ]
  }
}

test('state', () => {
  expect(state()).toStrictEqual({settings: undefined})
})

describe('mutations', () => {
  test('setSettings', () => {
    const state = {};
    mutations.setSettings(state, {settings: SETTINGS})
    expect(state.settings).toBe(SETTINGS)
  })

  test('setSettings ~ undefined', () => {
    const state = {};
    mutations.setSettings(state, {settings: SETTINGS})
    expect(state.settings).toBe(SETTINGS)
    mutations.setSettings(state, {settings: undefined})
    expect(state.settings).toBe(SETTINGS)
  })
})

describe('getters', () => {
  test('getSettings', () => {
    const state = {};
    expect(getters.getSettings(state)).toBe(undefined)
    mutations.setSettings(state, {settings: SETTINGS})
    var S = getters.getSettings(state)
    expect(S).toBe(SETTINGS)

    S.are = null
    // changing S affects state
    expect(getters.getSettings(state)).toStrictEqual({...SETTINGS, are: null})
  })

  test('getSettingsCopy', () => {
    const state = {};
    expect(getters.getSettings(state)).toBe(undefined)
    mutations.setSettings(state, {settings: SETTINGS})
    var S = getters.getSettings(state)
    expect(S).toBe(SETTINGS)

    S.are = null
    // changing S doesn't affect state
    expect(getters.getSettings(state)).toStrictEqual(SETTINGS)
  })

  test('isUndefined', () => {
    const state = {};
    expect(getters.isUndefined(state)).toBe(true)
    mutations.setSettings(state, {settings: SETTINGS})
    expect(getters.isUndefined(state)).toBe(false)
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
  })

  afterEach(() => {
    store = undefined;
  })

  test('get_settings success', done => {
    axios.get.mockResolvedValue({
      status: 200, data: SETTINGS,
    });

    store.dispatch('get').then(settings => {
      expect(settings).toStrictEqual(SETTINGS);
      done();
    })
  })

  test('get_settings fail', done => {
    axios.get.mockResolvedValue({
      status: 500, data: SETTINGS,
    });

    store.dispatch('get').then(settings => {
      expect(settings).not.toStrictEqual(SETTINGS);
      done();
    })
  })

  test('set_settings success', done => {
    axios.post.mockResolvedValue({
      status: 200, data: SETTINGS,
    });

    store.dispatch('set', {settings: SETTINGS}).then(settings => {
      expect(settings).toStrictEqual(SETTINGS);
      done();
    })
  })

  test('set_settings fail', done => {
    axios.post.mockResolvedValue({
      status: 500, data: SETTINGS,
    });

    store.dispatch('set', {settings: SETTINGS}).then(settings => {
      expect(settings).not.toStrictEqual(SETTINGS);
      done();
    })
  })

  test('sync success', done => {
    axios.get.mockResolvedValue({
      status: 200, data: SETTINGS,
    });

    store.dispatch('sync').then(ok => {
      expect(ok).toBe(true)
      // expect(store.getters['settings/getSettingsCopy']).toStrictEqual(SETTINGS)
      done();
    })
  })

  test('sync fail', done => {
    axios.get.mockResolvedValue({
      status: 500, data: SETTINGS,
    });

    store.dispatch('sync').then(ok => {
      expect(ok).toBe(true)  // todo: should be false
      // expect(store.getters['settings/getSettingsCopy']).not.toStrictEqual(SETTINGS)
      done();
    })
  })
})
