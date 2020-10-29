import {createLocalVue, mount} from "@vue/test-utils";
import {afterEach, beforeEach, describe, jest, test} from "@jest/globals";
import axios from 'axios';
import {
  BButton,
  BDropdown,
  BDropdownItem,
} from "bootstrap-vue";
import PageHeader from "../../../components/header/PageHeader";
import PageHeaderItem from "../../../components/header/PageHeaderItem";

import {AnalyzerState} from "../../../src/api";
import {COMMIT} from '../../../src/events';
import Vuex from "vuex";
import flushPromises from "flush-promises";
import result from "../result";
import {uuidv4} from "../../../src/util";
import ResultChartStack from "../../../components/results/ResultChartStack";

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
  return mount(result, {
    mocks: {
      $store: store,
      $route: {
        path: '/analysis/result', query: { id: ID }
      },
      $router: {
        push: jest.fn(),
      },
    },
    stubs: {
      PageHeader,
      PageHeaderItem,
      BButton,
      BDropdown,
      BDropdownItem,
      ResultChartStack: { template: '<div class="result-chart-stack-stub" />' },
    }
  })
}


test('mount & destroy', async () => {
  const w = factory();
  await flushPromises();

  // there is a header with some items & buttons
  expect(w.findAllComponents(PageHeader).wrappers.length).toBe(1);
  expect(w.findAllComponents(PageHeaderItem).wrappers.length).toBeGreaterThanOrEqual(1);
  expect(w.find('.run-selector').exists()).toBeTruthy();
  expect(w.find('.export-button').exists()).toBeTruthy();

  // there should be *no* ResultChartStack yet
  expect(w.findComponent(ResultChartStack).exists()).toBeFalsy();

  w.destroy();
});

describe('with results', () => {
  var w;
  var handleGetResult;

  beforeEach(async () => {
    handleGetResult = jest.spyOn(result.methods, 'handleGetResult');

    axios.get.mockResolvedValueOnce({  // get_db_id
      status: 200, data: 17,
    });
    axios.post.mockResolvedValueOnce({  // get_result_list todo: why is it a POST?!
      status: 200, data: [18, 19, 20],
    });
    axios.get.mockResolvedValueOnce({   // get_colors
      status: 200, data: ['#123456', '#456789']
    });
    axios.post.mockResolvedValueOnce({   // get_result todo: why is it a POST?!
      status: 200, data: { dummy: 'result' },
    });
    w = factory();
    await flushPromises();
  })

  test('mount', async () => {
    expect(handleGetResult).toHaveBeenCalled();
    // there should be a ResultChartStack
    expect(w.findComponent(ResultChartStack).exists()).toBeTruthy();
  });

  test('select run', async () => {
    expect(handleGetResult).toHaveBeenCalledTimes(1);

    axios.get.mockResolvedValueOnce({   // get_colors
      status: 200, data: ['#123456', '#456789']
    });
    axios.post.mockResolvedValueOnce({   // get_result todo: why is it a POST?!
      status: 200, data: { dummy: 'result' },
    });

    const item = w.findAllComponents(BDropdownItem).wrappers[1];
    await item.vm.$emit('click');
    await flushPromises();

    expect(handleGetResult).toHaveBeenCalledTimes(2);
  });

  test('export', async () => {
    await w.find('.export-button').trigger('click');
    await flushPromises();

    expect(axios.post).toHaveBeenCalledWith(`/api/db/export_result`, { analysis: 17, run: undefined });
  });
});
