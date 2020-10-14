import {createLocalVue, shallowMount} from "@vue/test-utils";
import Vuex from "vuex";
import {beforeEach, test} from "@jest/globals";
import flushPromises from "flush-promises";
import { readFileSync } from "fs";

import ResultChartStack from "../ResultChartStack";
import ResultChart from "../ResultChart";

import { labelCallback} from "../ResultChart";

const FEATURE = {
  options: ['Feature1', 'Feature2'],
  default: 'Feature1',
  labels: { Feature1: 'Feature 1', Feature2: 'Feature 2' },
  units: { Feature1: 'kg', Feature2: 'J' },
  descriptions: { Feature1: 'dummy feature 1', Feature2: 'dummy feature 2'},
};
const RESULTS = {
  Feature1: JSON.parse(readFileSync(__dirname + '/result1.json')),
  Feature2: JSON.parse(readFileSync(__dirname + '/result2.json')),
};
const COLORS = [
  '#002255', '#84204e', '#4e709e', '#ae5f85', '#89b9e8', '#e1abc0', '#8b95a2', '#74676b', '#353232',
];

var store;

function factory() {
  const localVue = createLocalVue();
  localVue.use(Vuex)

  store = new Vuex.Store({
    modules: {
      schemas: {
        namespaced: true,
        getters: {
          getFeature() {
            return FEATURE;
          },
        },
      },
    },
  });

  return shallowMount(
    ResultChartStack, {
      propsData: {
        raw_result: RESULTS,
        colors: COLORS,
      },
      mocks: {
        $store: store,
      },
      stubs: {
        ResultChart: ResultChart,
      },
    },
  )
}

test('mount', () => {
  const w = factory();  // todo: expand on this maybe...
});

test('ResultChart.labelCallback()', () => {
  const TOOLTIPITEM = {  // todo: should be in static/__tests__/results.test.js
    xLabel: 153.5,
    yLabel: 35.313579,
    datasetIndex: 3,
  }
  const DATA = {
    unit: 'µF',
    datasets: [
      {}, {}, {}, { label: 'Dummy label'}
    ]
  }

  const label = labelCallback(TOOLTIPITEM, DATA);
  expect(label).toMatch(/^.*: [0-9]{2}:[0-9]{2}.[0-9] ➔ [0-9]+.[0-9]{2} .*$/g);
  expect(label).toContain(DATA.datasets[3].label);
  expect(label).toContain(DATA.unit);
});

test('destroy', () => {
  const w = factory();  // todo: expand on this maybe...
  w.destroy();
});
