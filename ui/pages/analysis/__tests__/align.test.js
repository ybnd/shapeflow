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
import align from "../align";
import {uuidv4} from "../../../static/util";
import {cloneDeep} from 'lodash';

const ID = uuidv4();
const CONFIG = {
  name: '#1',
  transform: {
    roi: {},
    flip: {},
    turn: 0,
  }
}
const STATUS = {
  state: AnalyzerState.LAUNCHED
}
const SIZE = [1280, 720];
const ROI = {
  BL: { x: 0.2, y: 0.8 },
  TL: { x: 0.2, y: 0.2 },
  TR: { x: 0.8, y: 0.2 },
  BR: { x: 0.8, y: 0.8 },
};
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
})

afterEach(() => {
  jest.clearAllTimers();
  jest.clearAllMocks();

  // clear document
  document.body.innerHTML = '';
});

function factory() {
  return mount(align, {
    mocks: {
      $store: store,
      $route: {
        path: '/analysis/align', query: { id: ID }
      }
    },
    stubs: {
      PageHeader,
      PageHeaderItem,
      PageHeaderSeek: { template: '<div class="PageHeaderSeekStub" />' },
      BButton,
      BCard,
    },
    localVue,
  })
}


test('mount & destroy', async () => {
  const clearRoi = jest.spyOn(align.methods, 'clearRoi')

  const w = factory();
  await flushPromises();

  // there is a header with some items & buttons
  expect(w.findAllComponents(PageHeader).wrappers.length).toBe(1);
  expect(w.findAllComponents(PageHeaderItem).wrappers.length).toBeGreaterThan(1);
  expect(w.find('.align-clear').exists()).toBeTruthy();
  expect(w.find('.align-undo').exists()).toBeTruthy();
  expect(w.find('.align-redo').exists()).toBeTruthy();
  expect(w.find('.align-fliph').exists()).toBeTruthy();
  expect(w.find('.align-flipv').exists()).toBeTruthy();
  expect(w.find('.align-turncw').exists()).toBeTruthy();
  expect(w.find('.align-turnccw').exists()).toBeTruthy();
  expect(w.find('.align-bounds').exists()).toBeTruthy();

  // There should be an image streaming get_inverse_overlaid_frame
  const frame = w.find('.streamed-image-a')
  expect(frame.exists()).toBeTruthy();
  console.log(frame.element);
  expect(frame.element.src).toContain(ID);
  expect(frame.element.src).toContain('get_inverse_overlaid_frame');

  expect(analyzers_refresh).toHaveBeenCalled();

  // ROI is invalid, so clearRoi gets called
  expect(clearRoi).toHaveBeenCalled();

  w.destroy();

  // Inverse overlaid frame stream should have been stopped
  expect(axios.post).toHaveBeenCalledWith(`/api/stream/${ID}/get_inverse_overlaid_frame/stop`, {}, {})
});

test.todo('move to a different id')

test('streamed frame comes through', async () => {
  const updateFrame = jest.spyOn(align.methods, 'updateFrame')
  const resolveTransform = jest.spyOn(align.methods, 'resolveTransform');
  const clearRoi = jest.spyOn(align.methods, 'clearRoi');

  const w = factory();
  await flushPromises();

  expect(updateFrame).not.toHaveBeenCalled();
  expect(resolveTransform).not.toHaveBeenCalled();
  expect(clearRoi).toHaveBeenCalledTimes(1);
  expect(w.vm.$data.moveableShow).toBe(false);

  // Fake frame load
  w.vm.$refs.frame.getBoundingClientRect = jest.fn();
  w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
  await w.vm.$refs.frame.dispatchEvent(new Event('load'));

  expect(updateFrame).toHaveBeenCalled();
  expect(resolveTransform).toHaveBeenCalled();
  expect(clearRoi).toHaveBeenCalledTimes(1);
  expect(w.vm.$data.moveableShow).toBe(false);
  expect(w.vm.$data.align.frame).toStrictEqual(RECT);
});

test('backend provides valid roi', async () => {
  const updateFrame = jest.spyOn(align.methods, 'updateFrame');
  const resolveTransform = jest.spyOn(align.methods, 'resolveTransform');
  const clearRoi = jest.spyOn(align.methods, 'clearRoi');
  const handleShowMoveable = jest.spyOn(align.methods, 'handleShowMoveable')

  axios.get.mockResolvedValueOnce({
    status: 200, data: ROI
  });
  const w = factory();
  await flushPromises();

  expect(updateFrame).not.toHaveBeenCalled();
  expect(resolveTransform).toHaveBeenCalledTimes(1);
  expect(clearRoi).not.toHaveBeenCalled();
  expect(handleShowMoveable).not.toHaveBeenCalled();
  expect(w.vm.$data.moveableShow).toBe(false);

  // Fake frame load
  w.vm.$refs.frame.getBoundingClientRect = jest.fn();
  w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
  await w.vm.$refs.frame.dispatchEvent(new Event('load'));

  expect(updateFrame).toHaveBeenCalledTimes(1);
  expect(resolveTransform).toHaveBeenCalledTimes(2);
  expect(clearRoi).not.toHaveBeenCalled();
  expect(w.vm.$data.align.frame).toStrictEqual(RECT);
  expect(handleShowMoveable).toHaveBeenCalled();
  expect(w.vm.$data.moveableShow).toBe(true);
});

test.todo('resize');

describe('draw rectangle', () => {
  test('no moveable yet -> set roi', async () => {
    const updateRoiCoordinates = jest.spyOn(align.methods, 'updateRoiCoordinates');

    const w = factory();
    await flushPromises();

    // Fake frame load
    w.vm.$refs.frame.getBoundingClientRect = jest.fn();
    w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
    w.vm.$refs.frame.dispatchEvent(new Event('load'));
    expect(w.vm.$data.moveableShow).toBe(false);

    expect(updateRoiCoordinates).toHaveBeenCalledTimes(0);

    const content = w.find('.align');
    content.trigger('mousedown', { clientX: 150, clientY: 150 });
    content.trigger('mouseup', { clientX: 600, clientY: 600 });

    await flushPromises();
    jest.advanceTimersByTime(100); // resolve throttle/debounce

    // a new roi is created from the rectangle & sent to the backend
    expect(updateRoiCoordinates).toHaveBeenCalledTimes(1);
    expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/estimate_transform`, expect.anything(), expect.anything())
  });

  test('already has moveable -> do nothing', async () => {
    const resolveTransform = jest.spyOn(align.methods, 'resolveTransform');
    const updateRoiCoordinates = jest.spyOn(align.methods, 'updateRoiCoordinates');

    axios.get.mockResolvedValueOnce({
      status: 200, data: ROI
    });
    const w = factory();
    await flushPromises();

    // Fake frame load
    w.vm.$refs.frame.getBoundingClientRect = jest.fn();
    w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
    w.vm.$refs.frame.dispatchEvent(new Event('load'));
    expect(w.vm.$data.moveableShow).toBe(true);

    expect(updateRoiCoordinates).toHaveBeenCalledTimes(0);

    const content = w.find('.align');
    content.trigger('mousedown', { clientX: 150, clientY: 150 });
    content.trigger('mouseup', { clientX: 600, clientY: 600 });

    await flushPromises();
    jest.advanceTimersByTime(100); // resolve throttle/debounce

    // mouse events came through but didn't create a new roi
    expect(updateRoiCoordinates).toHaveBeenCalledTimes(0);
    expect(axios.post).not.toHaveBeenCalledWith(`/api/${ID}/call/estimate_transform`, expect.anything(), expect.anything())
  });
});


describe('with frame & roi', () => {
  var w;
  var moveable;
  var control_box;

  var handleTransform;

  beforeEach(async () => {
    handleTransform = jest.spyOn(align.methods, 'handleTransform');

    axios.get.mockResolvedValueOnce({
      status: 200, data: ROI
    });
    w = factory();
    await flushPromises();

    // Fake frame load
    w.vm.$refs.frame.getBoundingClientRect = jest.fn();
    w.vm.$refs.frame.getBoundingClientRect.mockReturnValue(RECT);
    w.vm.$refs.frame.dispatchEvent(new Event('load'));
    expect(w.vm.$data.moveableShow).toBe(true);

    control_box = document.getElementsByClassName('moveable-control-box')[0];
    moveable = w.find('.moveable');
  });

  describe('moveable', () => {
    test('renders properly', async () => {
      expect(document.getElementsByClassName('moveable-control-box').length).toBe(1);

      expect(document.getElementsByClassName('moveable-line').length).toBe(9);
      expect(document.getElementsByClassName('moveable-control').length).toBe(9);
    });

    // test('drag moveable', async () => {  // todo: can't figure out how to mock events on Moveable
    //   expect(handleTransform).not.toHaveBeenCalled();
    //
    //   await moveable.element.dispatchEvent(new Event('mousedown', { clientX: 150, clientY: 150 }));
    //   await moveable.element.dispatchEvent(new Event('mousemove', { offsetX: 50, offsetY: 50}));
    //   await moveable.element.dispatchEvent(new Event('mouseup', { clientX: 200, clientY: 200 }));
    //
    //   await flushPromises();
    //   jest.advanceTimersByTime(500);
    //   await w.vm.$nextTick();
    //
    //   expect(handleTransform).toHaveBeenCalled();
    // });

    test.todo('drag corner');

    test.todo('drag edge');

    test.todo('rotate');
  });

  describe('controls', () => {
    test('clear', async () => {
      expect(w.vm.$data.align.roi).toStrictEqual(ROI);
      expect(w.vm.$data.moveableShow).toBe(true);

      await w.find('.align-clear').trigger('click');
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/clear_roi`, expect.anything());
      expect(w.vm.$data.align.roi).toBeFalsy();
      expect(w.vm.$data.moveableShow).toBe(false);
    });

    test('undo', async () => {
      w.vm.$data.align.roi = undefined;
      expect(w.vm.$data.align.roi).toBe(undefined);

      axios.put.mockResolvedValueOnce({
        status: 200, data: { transform: { roi: ROI }}
      });
      await w.find('.align-undo').trigger('click');
      await flushPromises();

      expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/undo_config`, expect.anything(), expect.anything());
      expect(w.vm.$data.align.roi).toBe(ROI);
    });

    test('redo', async () => {
      w.vm.$data.align.roi = undefined;
      expect(w.vm.$data.align.roi).toBe(undefined);

      axios.put.mockResolvedValueOnce({
        status: 200, data: { transform: { roi: ROI }}
      });
      await w.find('.align-redo').trigger('click');
      await flushPromises();

      expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/redo_config`, expect.anything(), expect.anything());
      expect(w.vm.$data.align.roi).toBe(ROI);
    });

    test('flip H', async () => {
      axios.post.mockResolvedValueOnce({ status: 200});
      await w.find('.align-fliph').trigger('click');
      await flushPromises();

    expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/flip_h`, expect.anything());
    });

    test('flip V', async () => {
      axios.post.mockResolvedValueOnce({ status: 200});
      await w.find('.align-flipv').trigger('click');
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/flip_v`, expect.anything());
    });

    test('turn CW', async () => {
      axios.post.mockResolvedValueOnce({ status: 200});
      await w.find('.align-turncw').trigger('click');
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/turn_cw`, expect.anything());
    });

    test('turn CCW', async () => {
      axios.post.mockResolvedValueOnce({ status: 200});
      await w.find('.align-turnccw').trigger('click');
      await flushPromises();

      expect(axios.post).toHaveBeenCalledWith(`/api/${ID}/call/turn_ccw`, expect.anything());
    });

    test('bounds', async () => {
      expect(w.vm.$data.enforceBounds).toBe(true);
      expect(w.vm.$data.moveable.bounds).toBeTruthy();

      await w.find('.align-bounds').trigger('click');
      await flushPromises();

      expect(w.vm.$data.enforceBounds).toBe(false);
      expect(w.vm.$data.moveable.bounds).toBeFalsy();

      await w.find('.align-bounds').trigger('click');
      await flushPromises();

      expect(w.vm.$data.enforceBounds).toBe(true);
      expect(w.vm.$data.moveable.bounds).toBeTruthy();
    });
  });
});



