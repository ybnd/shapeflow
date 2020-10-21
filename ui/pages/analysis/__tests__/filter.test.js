import {createLocalVue, mount, shallowMount} from "@vue/test-utils";
import {afterAll, afterEach, beforeAll, beforeEach, describe, test, jest} from "@jest/globals";
import axios from 'axios';
import {
  BButton, BCard,
} from "bootstrap-vue";
import PageHeader from "../../../components/header/PageHeader";
import PageHeaderItem from "../../../components/header/PageHeaderItem";

import {
  AnalyzerState
} from "../../../static/api";
import Vuex from "vuex";
import VueRouter from "vue-router";
import flushPromises from "flush-promises";
import filter from "../filter";
import {uuidv4} from "../../../static/util";
import {cloneDeep} from 'lodash';
import align from "../align";
import PageHeaderSeek from "../../../components/header/PageHeaderSeek";
import ConfigSidebar from "../../../components/config/ConfigSidebar";

const ID = uuidv4();
const CONFIG = {
  name: '#1',
}
const STATUS = {
  state: AnalyzerState.CAN_FILTER
}
const SIZE = [1280, 720];
const RECT = {
  left: 120,  // sidebar
  top: 38,    // header
  right: 120 + SIZE[0],
  bottom: 38 + SIZE[1],
  width: SIZE[0],
  height: SIZE[1],
};

var localVue;
var store;

jest.mock('axios');
jest.useFakeTimers();
const analyzers_refresh = jest.fn();

beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex);

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state: require('../../../store/analyzers').state,
        mutations: require('../../../store/analyzers').mutations,
        getters: require('../../../store/analyzers').getters,
        actions: {
          refresh: analyzers_refresh,
        }
      },
    },
  })

  store.commit('analyzers/addAnalyzer', { id: ID });
  store.commit('analyzers/setAnalyzerConfig', { id: ID, config: CONFIG });
  store.commit('analyzers/setAnalyzerStatus', { id: ID, status: STATUS });
  store.commit('analyzers/addToQueue', { id: ID });

  // requests succeed with empty data by default
  axios.get.mockResolvedValue({ status: 200, data: undefined })
  axios.put.mockResolvedValue({ status: 200, data: undefined })
  axios.post.mockResolvedValue({ status: 200, data: undefined });
});

afterEach(() => {
  jest.clearAllTimers();
  jest.clearAllMocks();

  // clear document
  document.body.innerHTML = '';
});

function factory() {
  return mount(filter, {
    mocks: {
      $store: store,
      $route: {
        path: '/analysis/filter', query: { id: ID }
      },
      $router: {
        push: jest.fn(),
      },
    },
    stubs: {
      PageHeader,
      PageHeaderItem,
      PageHeaderSeek: { template: '<div class="PageHeaderSeekStub" />' },
      BButton,
      BCard,
      SchemaForm: { template: '<div class="schema-form-stub" />' },
    }
  })
}


test('mount & destroy', async () => {
  const w = factory();
  await flushPromises();

  // Advance timers so the frame reference can catch up
  jest.advanceTimersByTime(100);

  // there is a header with some items & buttons
  expect(w.findAllComponents(PageHeader).wrappers.length).toBe(1);
  expect(w.findAllComponents(PageHeaderItem).wrappers.length).toBeGreaterThan(1);
  expect(w.findAllComponents(PageHeaderSeek).wrappers.length).toBe(1);
  expect(w.find('.filter-clear').exists()).toBeTruthy();
  expect(w.find('.filter-undo').exists()).toBeTruthy();
  expect(w.find('.filter-redo').exists()).toBeTruthy();
  expect(w.find('.filter-toggle-sidebar').exists()).toBeTruthy();
  expect(w.find('.filter-toggle-frame').exists()).toBeTruthy();
  expect(w.find('.filter-toggle-state').exists()).toBeTruthy();
  expect(w.find('.filter-toggle-overlay').exists()).toBeTruthy();

  // There should be a <div class="filter" />
  const filter = w.find('.filter');
  expect(filter.element.tagName).toBe('DIV');

  // There should be an image streaming get_frame
  const frame = w.find('.streamed-image-f')
  expect(frame.exists()).toBeTruthy();
  expect(frame.element.src).toContain(ID);
  expect(frame.element.src).toContain('get_frame');

  // There should be an image streaming get_state_frame
  const state = w.find('.overlay-state')
  expect(state.exists()).toBeTruthy();
  expect(state.element.src).toContain(ID);
  expect(state.element.src).toContain('get_state_frame');

  // There should be an image with get_overlay_png
  const overlay = w.find('.overlay')
  expect(overlay.exists()).toBeTruthy();
  expect(overlay.element.src).toContain(ID);
  expect(overlay.element.src).toContain('get_overlay_png');

  expect(analyzers_refresh).toHaveBeenCalled();

  w.destroy();

  // Streams should be stopped
  expect(axios.post).toHaveBeenCalledWith(`/api/stream/${ID}/get_frame/stop`, {}, {})
  expect(axios.post).toHaveBeenCalledWith(`/api/stream/${ID}/get_state_frame/stop`, {}, {})
});

test('streamed frame comes through', async () => {
  const updateFrame = jest.spyOn(filter.methods, 'updateFrame');

  const w = factory();
  await flushPromises();

  // Fake frame load
  w.vm.$refs.frame.getBoundingClientRect = jest.fn();
  w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
  w.vm.$refs.frame.dispatchEvent(new Event('load'));
  await flushPromises();

  expect(updateFrame).toHaveBeenCalled();
  expect(w.vm.$data.filter.frame).toStrictEqual(RECT);
});

test('click to set filter', async () => {
  const w = factory();
  await flushPromises();

  // Fake frame load
  w.vm.$refs.frame.getBoundingClientRect = jest.fn();
  w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
  w.vm.$refs.frame.dispatchEvent(new Event('load'));
  await flushPromises();

  const CLICK = {
    clientX: 150, clientY: 150,
  }
  await w.find('.filter').trigger('click', CLICK);
  await flushPromises();

  expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/set_filter_click`, expect.anything(), expect.anything());
});

describe('controls', () => {
  var w;

  beforeAll(async () =>{
    w = factory();
    await flushPromises();

    // Fake frame load
    w.vm.$refs.frame.getBoundingClientRect = jest.fn();
    w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
    w.vm.$refs.frame.dispatchEvent(new Event('load'));
    await flushPromises();
  });

  test('clear', async () => {
    await w.find('.filter-clear').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/clear_filters`, expect.anything(), expect.anything());
  });

  test('redo', async () => {
    await w.find('.filter-undo').trigger('click');
    await flushPromises();

    expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/undo_config`, { context: 'masks' }, expect.anything());
  });

  test('undo', async () => {
    await w.find('.filter-redo').trigger('click');
    await flushPromises();

    expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/redo_config`, { context: 'masks' }, expect.anything());
  });

  test('toggle sidebar', async () => {
    expect(w.vm.$data.hideConfigSidebar).toBe(true);
    expect(w.findComponent(ConfigSidebar).exists()).toBeFalsy();
    expect(w.findAll('.with-cs').wrappers.length).toBe(0);


    await w.find('.filter-toggle-sidebar').trigger('click');
    await flushPromises();

    expect(w.vm.$data.hideConfigSidebar).toBe(false);
    expect(w.findComponent(ConfigSidebar).exists()).toBeTruthy();
    expect(w.findAll('.with-cs').wrappers.length).toBe(3);

    await w.find('.filter-toggle-sidebar').trigger('click');
    await flushPromises();

    expect(w.vm.$data.hideConfigSidebar).toBe(true);
    expect(w.findComponent(ConfigSidebar).exists()).toBeFalsy();
    expect(w.findAll('.with-cs').wrappers.length).toBe(0);
  });

  test('toggle images', async () => {
    expect(w.find('.streamed-image-f').exists()).toBe(true);
    expect(w.find('.overlay').exists()).toBe(true);
    expect(w.find('.overlay-state').exists()).toBe(true);

    await w.find('.filter-toggle-frame').trigger('click');
    await flushPromises();
    expect(w.find('.streamed-image-f').exists()).toBe(false);
    expect(w.find('.overlay').exists()).toBe(true);
    expect(w.find('.overlay-state').exists()).toBe(true);

    await w.find('.filter-toggle-overlay').trigger('click');
    await flushPromises();
    expect(w.find('.streamed-image-f').exists()).toBe(false);
    expect(w.find('.overlay').exists()).toBe(false);
    expect(w.find('.overlay-state').exists()).toBe(true);

    // when two images have been disabled, the last button can't be clicked
    await w.find('.filter-toggle-state').trigger('click');
    await flushPromises();
    expect(w.find('.streamed-image-f').exists()).toBe(false);
    expect(w.find('.overlay').exists()).toBe(false);
    expect(w.find('.overlay-state').exists()).toBe(true);

    await w.find('.filter-toggle-frame').trigger('click');
    await flushPromises();
    await w.find('.filter-toggle-overlay').trigger('click');
    await flushPromises();
    expect(w.find('.streamed-image-f').exists()).toBe(true);
    expect(w.find('.overlay').exists()).toBe(true);
    expect(w.find('.overlay-state').exists()).toBe(true);

    await w.find('.filter-toggle-state').trigger('click');
    await flushPromises();
    expect(w.find('.streamed-image-f').exists()).toBe(true);
    expect(w.find('.overlay').exists()).toBe(true);
    expect(w.find('.overlay-state').exists()).toBe(false);
  });
});
