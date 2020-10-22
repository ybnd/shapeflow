import {createLocalVue, mount, shallowMount} from "@vue/test-utils";
import {afterAll, afterEach, beforeAll, beforeEach, describe, test} from "@jest/globals";
import axios from 'axios';
import {
  BButton, BCard, BFormCheckbox,
  BFormGroup,
  BFormInput,
  BFormRow,
  BFormSelect,
  BInputGroup,
  BPopover,
  BRow,
  BTbody
} from "bootstrap-vue";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

import settings from '../settings';
import {retryOnce} from "../../src/util";
import {get_schemas, get_settings, clear_cache, clear_db, get_cache_size, open_root} from "../../src/api";
import Vuex from "vuex";
import flushPromises from "flush-promises";


const SCHEMA = { dummy: 'schema' };
var SETTINGS = { dummy: 'SETTINGS'};

var localVue;
var store;

const analyzers_newnotice = jest.fn();
const settings_set = jest.fn();
const settings_sync = jest.fn();

beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex);

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        mutations: {
          newNotice: analyzers_newnotice,
        },
      },
      schemas: {
        namespaced: true,
        getters: {
          getSettingsSchema() {
            return SCHEMA;
          }
        }
      },
      settings: {
        namespaced: true,
        getters: {
          getSettingsCopy() {
            return SETTINGS;
          }
        },
        actions: {
          set: settings_set,
          sync: settings_sync,
        }
      },
    },
  });
});

jest.mock('axios');

axios.get.mockResolvedValue({
  status: 200, data: 1000,  // mock db/cache size responses
})

afterEach(() => {
  jest.clearAllMocks();
})


function factory() {
  return mount(settings, {
    mocks: { $store: store },
    stubs: {
      PageHeader,
      PageHeaderItem,
      SchemaForm: { template: '<div class="form-stub" />' },
      BButton,
      BCard,
    }
  })
}


test('mount', async () => {
  const w = factory();

  // there is a header with some items & buttons
  expect(w.findAllComponents(PageHeader).wrappers.length).toBe(1);
  expect(w.findAllComponents(PageHeaderItem).wrappers.length).toBeGreaterThan(1);
  expect(w.find('.settings-open-root').exists()).toBeTruthy();
  expect(w.find('.settings-save').exists()).toBeTruthy()
  expect(w.find('.settings-clear-db').exists()).toBeTruthy()
  expect(w.find('.settings-clear-cache').exists()).toBeTruthy()

  // there is a form
  expect(w.find('.form-stub').exists()).toBeTruthy();

  expect(settings_sync).toHaveBeenCalled();
  // expect(axios.get).toHaveBeenCalledWith('/api/db/disk-size', expect.anything(), expect.anything());
  expect(axios.get).toHaveBeenCalledWith('/api/cache/disk-size', expect.anything());
});

test('set settings', async () => {
  const w = factory();

  expect(settings_set).not.toHaveBeenCalled();
  await w.find('.settings-save').trigger('click');
  expect(settings_set).toHaveBeenCalledWith(expect.anything(), { settings: SETTINGS });
});

test('clear db', async () => {
  const w = factory();

  expect(axios.post).not.toHaveBeenCalled();
  axios.post.mockResolvedValueOnce({
    status: 200, data: true,
  })
  await w.find('.settings-clear-db').trigger('click');
  expect(axios.post).toHaveBeenCalledWith('/api/db/forget', expect.anything(), expect.anything());
});

test('clear cache', async () => {
  const w = factory();

  expect(axios.post).not.toHaveBeenCalled();
  axios.post.mockResolvedValueOnce({
    status: 200, data: true,
  })
  await w.find('.settings-clear-cache').trigger('click');
  expect(axios.post).toHaveBeenCalledWith('/api/cache/clear', expect.anything(), expect.anything());
});

test('open root', async () => {
  const w = factory();

  expect(axios.post).not.toHaveBeenCalled();

  // open root
  axios.post.mockResolvedValue({
    status: 200, data: true,
  })
  await w.find('.settings-open-root').trigger('click');
  expect(axios.post).toHaveBeenCalledWith('/api/open_root', expect.anything(), expect.anything());
  expect(analyzers_newnotice).not.toHaveBeenCalled();

  // can't open root
  axios.post.mockResolvedValueOnce({
    status: 404, data: null,
  });
  await w.find('.settings-open-root').trigger('click');
  await flushPromises();
  expect(axios.post).toHaveBeenCalledWith('/api/open_root', expect.anything(), expect.anything());
  expect(analyzers_newnotice).toHaveBeenCalled();
});

