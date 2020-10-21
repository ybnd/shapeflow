import {createLocalVue, mount, shallowMount} from "@vue/test-utils";
import {afterEach, beforeEach, describe, test} from "@jest/globals";
import {cloneDeep} from 'lodash';

import Vuex from "vuex";
import {bPopoverJsDomHack, uuidv4} from "../../src/util";
import {BButton, BPopover,} from "bootstrap-vue";
import index from "../index";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
import {AnalyzerState, QueueState} from "../../src/api";
import flushPromises from "flush-promises";


var localVue;
var store;


const q_start = jest.fn();
const q_stop = jest.fn();
const q_clear = jest.fn();


// For making <b-popover> render properly in JSDOM
// https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/src/components/popover/popover.spec.js
const originalWindow = cloneDeep(window);
const originalDocument = cloneDeep(document);
const originalCreateRange = document.createRange;
const origGetBCR = Element.prototype.getBoundingClientRect;


beforeEach(() => {
  bPopoverJsDomHack();

  localVue = createLocalVue();
  localVue.use(Vuex);

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state: require('../../store/analyzers').state,
        getters: require('../../store/analyzers').getters,
        mutations: require('../../store/analyzers').mutations,
        actions: {
          q_start: q_start,
          q_stop: q_stop,
          q_clear: q_clear,
        },
      },
    }
  });
});

afterEach(() => {
  jest.clearAllMocks();

  // Remove any leftover popovers
  const popover_candidates = document.getElementsByClassName('popover');
  for (const popover of popover_candidates) {
    popover.remove();
  }

  // Reset overrides
  window = originalWindow;
  document = originalDocument;
  document.createRange = originalCreateRange;
  Element.prototype.getBoundingClientRect = origGetBCR;
})


function add(queue, status) {
  for (const id of queue) {
    store.commit('analyzers/addAnalyzer', { id: id });
    store.commit("analyzers/setAnalyzerStatus", { id: id, status: status });
    store.commit("analyzers/addToQueue", { id: id });
  }
}

function remove(queue) {
  for (const id of queue) {
    store.commit('analyzers/dropFromQueue', { id: id });
    store.commit('analyzers/dropAnalyzer', { id: id });
  }
}

function factory() {
  return mount(index, {
    mocks: { $store: store },
    stubs: {
      PageHeader,
      PageHeaderItem,
      'b-button': BButton,
      'b-popover': BPopover,
    },
    localVue,
  })
}


test('mount', () => {
  const w = factory();

  // There should be a header with 1 item
  expect(w.findComponent(PageHeader).exists()).toBeTruthy();
  expect(w.findAllComponents(PageHeaderItem).wrappers).toHaveLength(1);

  // There should be 3 buttons, all disabled
  expect(w.find('.start-queue').attributes('disabled')).toBeTruthy();
  expect(w.find('.stop-queue').attributes('disabled')).toBeTruthy();
  expect(w.find('.clear-queue').attributes('disabled')).toBeTruthy();

  // There should be a queue info section
  expect(w.find('.queue-info').exists()).toBeTruthy()
});

describe('queue status', () => {
  test('empty, stopped', () => {
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED });
    const w = factory();

    expect(w.find('.queue-info').text()).toBe('No analyses queued.')
  });

  test('multiple, stopped, not done', () => {
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED });

    add(Array(3).fill(null).map(uuidv4), { progress: 1, status: AnalyzerState.DONE });
    add([uuidv4()], { progress: 0.3, status: AnalyzerState.ANALYZING })
    add(Array(2).fill(null).map(uuidv4), { progress: 0, status: AnalyzerState.CAN_ANALYZE })

    const w = factory();

    expect(w.find('.queue-info').text()).toBe('6 analyses queued.')
  });

  test('one, stopped, progress', () => {
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED });

    add([uuidv4()], { progress: 0.3, status: AnalyzerState.ANALYZING })

    const w = factory();

    expect(w.find('.queue-info').text()).toBe('1 analysis queued.')
  });

  test('multiple, stopped, some done', () => {
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED });

    add(Array(3).fill(null).map(uuidv4), { progress: 1, state: AnalyzerState.DONE });
    add([uuidv4()], { progress: 0.3, state: AnalyzerState.ANALYZING })
    add(Array(2).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE })

    const w = factory();

    expect(w.find('.queue-info').text()).toBe('6 analyses queued (3 done).')
  });

  test('multiple, running, not done', () => {
    store.commit('analyzers/setQueueState', { queue_state: QueueState.RUNNING });

    add(Array(3).fill(null).map(uuidv4), { progress: 1, state: AnalyzerState.DONE });
    add([uuidv4()], { progress: 0.3, state: AnalyzerState.ANALYZING })
    add(Array(2).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE })

    const w = factory();

    expect(w.find('.queue-info').text()).toBe('Analyzing queue: 55% (3/6 done)')
  });
});

describe('start queue', () => {
  const BUTTON = '.start-queue';

  test('ok', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeFalsy();
    await w.find(BUTTON).trigger('click');
    await flushPromises();
    await w.vm.$forceUpdate();
    expect(q_start).toHaveBeenCalled();
  });

  test('disconnected', async () => {
    store.commit('analyzers/setIsConnected', { connected: false });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });

  test('empty', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED })
    // add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });

  test('running', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.RUNNING })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });
});

describe('stop queue', () => {
  const BUTTON = '.stop-queue';

  test('ok', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.RUNNING })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeFalsy();
    await w.find(BUTTON).trigger('click');
    await flushPromises();
    await w.vm.$forceUpdate();
    expect(q_stop).toHaveBeenCalled();
  });

  test('disconnected', async () => {
    store.commit('analyzers/setIsConnected', { connected: false });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.RUNNING })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });

  test('empty', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.RUNNING })
    // add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });

  test('stopped', async () => {
    store.commit('analyzers/setIsConnected', { connected: true });
    store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED })
    add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });

    const w = factory();

    expect(w.find(BUTTON).attributes('disabled')).toBeTruthy();
  });
});

// describe('clear queue', () => {  // todo: can't find popover in document :(
//   var w;
//   var clear;
//   var popover;
//
//   beforeEach(() => {
//     store.commit('analyzers/setIsConnected', { connected: true });
//     store.commit('analyzers/setQueueState', { queue_state: QueueState.STOPPED })
//     add(Array(3).fill(null).map(uuidv4), { progress: 0, state: AnalyzerState.CAN_ANALYZE });
//
//     w = factory();
//
//     clear = w.find('.clear-queue');
//     popover = w.findComponent(BPopover);
//   });
//
//   test('clear -> dismiss', async () => {
//     expect(clear.attributes('disabled')).toBeFalsy();
//
//     expect(document.getElementsByClassName('clear-queue-popover').length).toBe(0);
//
//     await clear.trigger('click')
//     await w.vm.$nextTick();
//     await flushPromises();
//     await w.vm.$forceUpdate();
//
//     expect(w.vm.$data.show_popover).toBe(true);
//     expect(document.getElementsByClassName('popover').length).toBe(1);
//
//     const dismiss = document.getElementsByClassName('clear-dismiss')[0];
//     await dismiss.click();
//
//     expect(w.vm.$data.show_popover).toBe(false);
//   });
//
//   test('clear -> confirm', async() => {
//     expect(clear.attributes('disabled')).toBeFalsy();
//
//     // click to show popover
//     await clear.trigger('click')
//   });
// });
