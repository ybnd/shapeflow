import {createLocalVue, shallowMount} from "@vue/test-utils";
import {afterEach, beforeEach, test} from "@jest/globals";

import {getters, mutations} from '../../../store/analyzers';

import Vuex from "vuex";
import {uuidv4} from "../../../static/util";
import ConfigSidebar from "../ConfigSidebar";
import {COMMIT} from "../../../static/events";
import flushPromises from "flush-promises";

const ID = uuidv4();
const CONFIG = { name: 'config' };
const SET_TO = { name: 'change' };
const SCHEMA = { dummy: 'schema' };

var localVue;
var store;

const set_config = jest.fn();
const getConfigSchema = jest.fn();

getConfigSchema.mockReturnValue(SCHEMA);

beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex)

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state() {
          return {
            config: { [ID]: CONFIG },
          }
        },
        mutations,
        getters,
        actions: {
          set_config,
        }
      },
      schemas: {
        namespaced: true,
        getters: {
          getConfigSchema,
        },
      }
    }
  })
});

function factory(hidden = false) {
  return shallowMount(ConfigSidebar, {
    propsData: { hidden, id: ID },
    mocks: { $store: store },
    stubs: {
      SchemaForm: { template: '<div class="schema-form-stub" />' }
    },
    localVue,
  })
}

afterEach(() => {
  jest.clearAllMocks();
});

test('mount & destroy', () => {
  const w = factory();

  const form = w.find('.schema-form-stub');
  expect(form.exists()).toBe(true);

  w.destroy();
});

test('update on store change', async () => {
  const w = factory();

  // force waiting -> true
  await w.setData({ waiting: true });

  store.commit('analyzers/setAnalyzerConfig', { id: ID, config: SET_TO });
  await w.vm.$nextTick();

  // ConfigSidebar.handleGetConfig should have been called
  expect(w.vm.$data.waiting).toBe(false);
});

test('handle form commit', async () => {
  const w = factory();
  expect(set_config).not.toHaveBeenCalled();

  // form emits a COMMIT event
  await w.find('.schema-form-stub').vm.$emit(COMMIT);
  await flushPromises();

  // sidebar should dispatch set_config
  expect(set_config).toHaveBeenCalled();
});
