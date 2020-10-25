import {createLocalVue, mount} from "@vue/test-utils";
import {afterEach, beforeEach, describe, jest, test} from "@jest/globals";
import axios from 'axios';
import {
  BButton,
  BCard,
  BDropdownItem,
  BFormGroup,
  BFormInput,
  BFormTextarea,
  BInputGroup,
  BInputGroupText,
  BRow
} from "bootstrap-vue";
import PageHeader from "../../../components/header/PageHeader";
import PageHeaderItem from "../../../components/header/PageHeaderItem";

import {AnalyzerState} from "../../../src/api";
import {COMMIT} from '../../../src/events';
import Vuex from "vuex";
import flushPromises from "flush-promises";
import configure from "../configure";
import {uuidv4} from "../../../src/util";
import BasicConfig from "../../../components/config/BasicConfig";
import SchemaForm from "../../../components/config/SchemaForm";

const ID = uuidv4();
const CONFIG = {
  name: '#1',
  description: 'dummy config',
  features: [],
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

const analyzers_get_config = jest.fn();
const analyzers_set_config = jest.fn();

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
          get_config: analyzers_get_config,
          set_config: analyzers_set_config,
        },
      },
      schemas: {
        namespaced: true,
        getters: {
          getConfigSchema() {
            return { properties: {} };
          },
        },
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
  return mount(configure, {
    mocks: {
      $store: store,
      $route: {
        path: '/analysis/configure', query: { id: ID }
      },
      $router: {
        push: jest.fn(),
      },
    },
    stubs: {
      PageHeader,
      PageHeaderItem,
      BButton,
      BCard,
      BRow,
      BFormGroup,
      BInputGroup,
      BFormInput,
      BDropdownItem,
      BInputGroupText,
      BFormTextarea,
      BasicConfig: { template: '<div class="basic-config-stub" />' },
      SchemaForm: { template: '<div class="schema-form-stub" />' },
    }
  })
}


test('mount & destroy', async () => {
  const w = factory();
  await flushPromises();

  expect(analyzers_get_config).toHaveBeenCalled();

  // there is a header with some items & buttons
  expect(w.findAllComponents(PageHeader).wrappers.length).toBe(1);
  expect(w.findAllComponents(PageHeaderItem).wrappers.length).toBeGreaterThan(1);
  expect(w.find('.configure-reset').exists()).toBeTruthy();
  expect(w.find('.configure-undo').exists()).toBeTruthy();
  expect(w.find('.configure-redo').exists()).toBeTruthy();

  // There should be a name/description section
  expect(w.find('.name-config').exists()).toBeTruthy();

  expect(w.vm.$data.ready).toStrictEqual({ schema: true, config: true });

  // There should be a BasicConfig section
  expect(w.find('.basic-config-container').exists()).toBeTruthy();
  expect(w.findComponent(BasicConfig).exists()).toBeTruthy();

  // There should be a FormSchema for the other stuff
  expect(w.find('.advanced-config-box').exists()).toBeTruthy();
  expect(w.findComponent(SchemaForm).exists()).toBeTruthy();

  w.destroy();
});

describe('controls', () => {
  test('reset to defaults', async () => {
    const w = factory();
    await flushPromises();

    expect(store.state.analyzers.notices.length).toBe(0);

    await w.find('.configure-reset').trigger('click');
    await flushPromises();

    expect(store.state.analyzers.notices.length).toBe(1);
  });

  test('undo', async () => {
    const w = factory();
    await flushPromises();

    await w.find('.configure-undo').trigger('click');
    await flushPromises();

    expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/undo_config`, { context: null }, expect.anything());
  });

  test('redo', async () => {
    const w = factory();
    await flushPromises();

    await w.find('.configure-redo').trigger('click');
    await flushPromises();

    expect(axios.put).toHaveBeenCalledWith(`/api/${ID}/call/redo_config`, { context: null }, expect.anything());
  });
});

describe('changes', () => {
  test('change name & keyup.enter', async () => {
    const w = factory();
    await flushPromises();

    expect(analyzers_set_config).not.toHaveBeenCalled();

    // trigger event & wait for throttle/debounce to catch up
    w.find('.configure-name').trigger('keyup.enter');
    jest.advanceTimersByTime(500);

    expect(analyzers_set_config).toHaveBeenCalled();
  });

  test('change name & focusout', async () => {
    const w = factory();
    await flushPromises();

    expect(analyzers_set_config).not.toHaveBeenCalled();

    // trigger event & wait for throttle/debounce to catch up
    w.find('.configure-name').trigger('focusout');
    jest.advanceTimersByTime(500);

    expect(analyzers_set_config).toHaveBeenCalled();
  });

  test('change description & focusout', async () => {
    const w = factory();
    await flushPromises();

    expect(analyzers_set_config).not.toHaveBeenCalled();

    // trigger event & wait for throttle/debounce to catch up
    w.find('.description-box').trigger('focusout');
    jest.advanceTimersByTime(500);

    expect(analyzers_set_config).toHaveBeenCalled();
  });

  test('change BasicConfig -> commit', async () => {
    const w = factory();
    await flushPromises();

    expect(analyzers_set_config).not.toHaveBeenCalled();

    // trigger event & wait for throttle/debounce to catch up
    w.findComponent(BasicConfig).vm.$emit(COMMIT);
    jest.advanceTimersByTime(500);

    expect(analyzers_set_config).toHaveBeenCalled();
  });

  test('change SchemaForm -> commit', async () => {
    const w = factory();
    await flushPromises();

    expect(analyzers_set_config).not.toHaveBeenCalled();

    // trigger event & wait for throttle/debounce to catch up
    w.findComponent(SchemaForm).vm.$emit(COMMIT);
    jest.advanceTimersByTime(500);

    expect(analyzers_set_config).toHaveBeenCalled();
  });
});
