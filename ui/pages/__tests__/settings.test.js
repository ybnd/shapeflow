import {createLocalVue, mount, shallowMount} from "@vue/test-utils";
import {afterAll, afterEach, beforeAll, beforeEach, describe, test} from "@jest/globals";
import {cloneDeep} from 'lodash';
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
import {killServer, startServer} from "../../static/shapeflow";
import {retryOnce} from "../../static/util";
import {waitSync} from "../../static/shapeflow";
import {get_schemas, get_settings, clear_cache, clear_db, get_cache_size, open_root} from "../../static/api";
import Vuex from "vuex";
import SchemaForm from "../../components/config/SchemaForm";
import SchemaCategory from "../../components/config/SchemaCategory";
import SchemaDefinition from "../../components/config/SchemaDefinition";
import SchemaField from "../../components/config/SchemaField";


var SCHEMAS;
var SETTINGS;

var localVue;
var store;

const analyzers_newnotice = jest.fn();
const settings_set = jest.fn();
const settings_sync = jest.fn();


beforeAll(async () => {
  startServer();
  SCHEMAS = await retryOnce(get_schemas);  // todo: use sf.py dump & mock axios instead
  SETTINGS = await retryOnce(get_settings);
});

afterAll(() => {
  killServer();
});

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
            return SCHEMAS.settings;
          }
        }
      },
      settings: {
        namespaced: true,
        getters: {
          getSettingsCopy() {
            return cloneDeep(SETTINGS);
          }
        },
        actions: {
          set: settings_set,
          sync: settings_set,
        }
      },
    },
  });
});


function factory() {
  return mount(settings, {
    mocks: { $store: store },
    stubs: {
      PageHeader,
      PageHeaderItem,
      SchemaForm,
      SchemaCategory,
      SchemaDefinition,
      SchemaField,
      BButton,
      BCard,
      BRow,
      BFormRow,
      BFormGroup,
      BInputGroup,
      BFormSelect,
      BFormInput,
      BFormCheckbox,
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
  expect(w.findAllComponents(SchemaForm).wrappers.length).toBeGreaterThan(1);
  expect(w.findAllComponents(SchemaCategory).wrappers.length).toBeGreaterThan(1);
  expect(w.findAllComponents(SchemaField).wrappers.length).toBeGreaterThan(1);
});
