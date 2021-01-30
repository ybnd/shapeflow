import {createLocalVue, mount} from "@vue/test-utils";
import {afterEach, beforeAll, beforeEach, describe, test} from "@jest/globals";
import {isEmpty, clone} from 'lodash';

import Vuex from "vuex";
import {retryOnce} from "../../../src/util";
import {readFileSync} from "fs";
import {
  BButton,
  BCol,
  BContainer,
  BDropdown, BDropdownItem,
  BFormCheckbox,
  BFormGroup,
  BFormInput,
  BFormRow,
  BFormSelect,
  BInputGroup,
  BInputGroupPrepend,
  BInputGroupText,
  BRow
} from "bootstrap-vue";

import BasicConfig from "../BasicConfig";
import SchemaField from "../SchemaField";
import {killServer, startServer} from "../../../src/shapeflow";
import axios from "axios";
import {api, url} from "../../../src/api";
import flushPromises from "flush-promises";
import {COMMIT} from "../../../src/events";


var localVue;
var store;
var emit;

const axios_get = jest.spyOn(axios, 'get');
const axios_put = jest.spyOn(axios, 'put');
const axios_post = jest.spyOn(axios, 'post');

const schemas_sync = jest.fn();

var SCHEMAS;
const FULL_CONFIG = JSON.parse(readFileSync(__dirname + '/config.json'));
const CONFIG = BasicConfig.props.config.default();

const RECENT_PATHS = {
  'video_path': ['a', 'b', 'c'],
  'design_path': ['d', 'e', 'f'],
}

beforeAll(async () => {
  startServer();
  SCHEMAS = await retryOnce(api.schemas);
  killServer();
});

beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex);

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state: require('../../../store/analyzers').state,
        getters: require('../../../store/analyzers').getters,
        mutations: require('../../../store/analyzers').mutations,
        actions: {

        },
      },
      schemas: {
        namespaced: true,
        state: require('../../../store/schemas').state,
        getters: require('../../../store/schemas').getters,
        mutations: require('../../../store/schemas').mutations,
        actions: {
          sync: schemas_sync,
        }
      },
    }

  });

  store.commit('schemas/setConfigSchema', { schema: SCHEMAS.config });

  axios_get.mockResolvedValueOnce({
    status: 200, data: RECENT_PATHS,
  });
});

function factory(config = undefined, staticPaths) {
  return mount(BasicConfig, {
    propsData: { config },
    mocks: { $store: store },
    stubs: {
      SchemaField,
      'b-container': BContainer,
      'b-row': BRow,
      'b-col': BCol,
      'b-form-row': BFormRow,
      'b-form-group': BFormGroup,
      'b-input-group': BInputGroup,
      'b-input-group-prepend': BInputGroupPrepend,
      'b-input-group-text': BInputGroupText,
      'b-form-select': BFormSelect,
      'b-form-input': BFormInput,
      'b-form-checkbox': BFormCheckbox,
      'b-button': BButton,
      'b-dropdown': BDropdown,
      'b-dropdown-item': BDropdownItem,
    }
  })
}

afterEach(() => {
  jest.clearAllMocks();
});


test('mount & destroy', () => {
  axios_put.mockResolvedValue({
    status: 200, data: true,
  })

  const w = factory();

  // video file & design file
  expect(w.findAll('.path-row').wrappers.length).toBe(2);
  expect(w.findAll('.path-browse').wrappers.length).toBe(2);
  expect(w.findAll('.path-select').wrappers.length).toBe(2);
  expect(w.findAll('.path-input').wrappers.length).toBe(2);

  // frame settings
  expect(w.findAll('.fis-selector').exists()).toBe(true);
  expect(w.findAll('.fis-value').exists()).toBe(true);

  // feature settings (no features present by default!)
  expect(w.findAll('.feature-row').exists()).toBe(false);
  expect(w.findAll('.feature-selector').exists()).toBe(false);
  expect(w.findAll('.parameter-col').exists()).toBe(false);

  expect(w.findAll('.add-button').exists()).toBe(true);

  w.destroy();
});

describe('files', () => {
  var w;
  var path = {};
  var browse = {};
  var select = {};
  const PATH_TO = 'z';

  beforeEach(async () => {
    axios_put.mockResolvedValue({
      status: 200, data: false,
    });

    w = factory(CONFIG);
    path = {
      video: w.findAll('.path-input').wrappers[0],
      design: w.findAll('.path-input').wrappers[1],
    }
    select = {
      video: w.findAll('.path-select').wrappers[0],
      design: w.findAll('.path-select').wrappers[1],
    }
    browse = {
      video: w.findAll('.path-browse').wrappers[0],
      design: w.findAll('.path-browse').wrappers[1],
    }
    emit = jest.spyOn(w.vm, '$emit');
    await flushPromises();
  })

  test('change -> check', async () => {
    async function _test(path, type) {
      axios_put.mockClear();
      emit.mockClear();

      await w.setProps({ config: { ...CONFIG, [`${type}_path`]: PATH_TO }})   // todo: not really testing the v-model part

      await path.trigger('change');
      await flushPromises();

      expect(axios_put).toHaveBeenCalledWith(url('fs', 'check_' + type), { path: PATH_TO });
      expect(emit).toHaveBeenCalledWith(COMMIT);
    }

    // video_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(path.video, 'video');
    expect(path.video.classes()).toContain('is-valid');

    // video_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(path.video, 'video');
    expect(path.video.classes()).toContain('is-invalid');

    // design_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(path.design, 'design');
    expect(path.design.classes()).toContain('is-valid');

    // design_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(path.design, 'design');
    expect(path.design.classes()).toContain('is-invalid');
  });

  test('select from dropdown -> check', async () => {
    const INDEX = 1;

    async function _test(select, type) {
      axios_put.mockClear();
      emit.mockClear();

      const item = select.findAll('.path-dropdown-item').wrappers[INDEX];
      await item.vm.$emit('click');
      await flushPromises();

      expect(axios_put).toHaveBeenCalledWith(url('fs', 'check_' + type), { path: RECENT_PATHS[`${type}_path`][INDEX] });
      expect(emit).toHaveBeenCalledWith(COMMIT);
    }

    // video_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(select.video, 'video');
    expect(path.video.classes()).toContain('is-valid');

    // video_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(select.video, 'video');
    expect(path.video.classes()).toContain('is-invalid');

    // design_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(select.design, 'design');
    expect(path.design.classes()).toContain('is-valid');

    // design_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(select.design, 'design');
    expect(path.design.classes()).toContain('is-invalid');
  });

  test('browse -> check -> ok', async () => {
    axios_get.mockResolvedValue({ status: 200, data: PATH_TO });

    async function _test(browse, type) {
      axios_put.mockClear();
      emit.mockClear();

      await browse.element.click();
      await flushPromises();

      expect(axios_put).toHaveBeenCalledWith(url('fs', 'check_' + type), { path: PATH_TO });
      expect(emit).toHaveBeenCalledWith(COMMIT);
    }

    // video_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(browse.video, 'video');
    expect(path.video.classes()).toContain('is-valid');

    // video_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(browse.video, 'video');
    expect(path.video.classes()).toContain('is-invalid');

    // design_path -> ok
    axios_put.mockResolvedValueOnce({ status: 200, data: true });
    await _test(browse.design, 'design');
    expect(path.design.classes()).toContain('is-valid');

    // design_path -> nok
    axios_put.mockResolvedValueOnce({ status: 200, data: false });
    await _test(browse.design, 'design');
    expect(path.design.classes()).toContain('is-invalid');
  });
});

describe('frame settings', () => {
  var w;
  var select;
  var label;
  var value;
  var OPTIONS;
  var DESCRIPTIONS;

  beforeEach(() => {
    axios_get.mockResolvedValueOnce({
      status: 200, data: RECENT_PATHS,
    });
    axios_put.mockResolvedValue({
      status: 200, data: true,
    });

    w = factory(CONFIG);
    select = w.find('.fis-selector');
    label = w.find('.fis-label');
    value = w.find('.fis-value');

    emit = jest.spyOn(w.vm, '$emit');

    OPTIONS = store.getters['schemas/getFrameIntervalSetting'].options;
    DESCRIPTIONS = store.getters['schemas/getFrameIntervalSetting'].descriptions;
  });

  test('select', async () => {
    for (const FIS of OPTIONS) {
      emit.mockClear();
      w.vm.$props.config.frame_interval_setting = FIS;  // todo: not really testing the v-model part

      await select.trigger('change', FIS);
      await w.vm.$forceUpdate();

      expect(label.text()).toBe(DESCRIPTIONS[FIS]);
      expect(emit).toBeCalledWith(COMMIT);
    }
  });

  test('select -> set value', async () => {
    const SET_TO = 10;

    for (const FIS of OPTIONS) {
      emit.mockClear();

      w.vm.$props.config.frame_interval_setting = FIS;  // todo: not really testing the v-model part
      w.vm.$props.config[FIS] = SET_TO;

      await value.trigger('change');
      await w.vm.$forceUpdate();

      expect(label.text()).toBe(DESCRIPTIONS[FIS]);
      expect(emit).toBeCalledWith(COMMIT);
    }
  });
});

describe('features', () => {
  var OPTIONS;
  var DEFAULTS;
  var PARAMETERS;

  beforeEach(() => {
    OPTIONS = store.getters['schemas/getFeature'].options;
    DEFAULTS = store.getters['schemas/getFeature'].defaults;
    PARAMETERS = store.getters['schemas/getFeature'].parameters;
  });

  test('add', async () => {
    const w = factory(CONFIG);

    // empty feature array -> a single feature gets added by default
    expect(w.vm.$props.config.features.length).toBe(1);
    // expect(w.findAll('.feature-selector').length).toBe(1);  // todo: but selector is not rendered for some reason?

    // add two more features
    const add = w.find('.add-button');
    await add.trigger('click');
    await add.trigger('click');
    await w.vm.$forceUpdate();

    expect(w.vm.$props.config.features.length).toBe(3);
    expect(w.findAll('.feature-selector').length).toBe(3);
  });

  test('mount with undefined features & parameters', async () => {
    const w = factory({ ...CONFIG, features: undefined, feature_parameters: undefined });
    await w.vm.$forceUpdate();

    expect(w.vm.$props.config.features.length).toBe(1);
    expect(w.findAll('.feature-selector').length).toBe(1);
  });

  test('remove', async () => {
    // start out with 3 features
    const w = factory({ ...CONFIG, features: clone(OPTIONS) });

    expect(w.vm.$props.config.features.length).toBe(3);
    expect(w.findAll('.feature-selector').wrappers.length).toBe(3);

    // remove the second feature
    await w.findAll('.remove-button').wrappers[1].trigger('click');
    await w.vm.$forceUpdate();
    expect(w.vm.$props.config.features.length).toBe(2);
    expect(w.findAll('.feature-selector').wrappers.length).toBe(2);

    // remove the first feature
    await w.findAll('.remove-button').wrappers[0].trigger('click');
    await w.vm.$forceUpdate();
    expect(w.vm.$props.config.features.length).toBe(1);
    expect(w.findAll('.feature-selector').wrappers.length).toBe(1);

    // there should be no remove buttons left, since there's only one feature now
    expect(w.find('.remove-button').exists()).toBeFalsy();
  });

  test('select', async () => {
    // start out with 3 features
    const w = factory({
      ...CONFIG,
      features: clone(OPTIONS),
      feature_parameters: OPTIONS.map(v => DEFAULTS[v])
    });
    await w.vm.$forceUpdate();
    emit = jest.spyOn(w.vm, '$emit');

    async function _test(index, option) {
      // set the second feature to the second option
      await w.findAll('.feature-selector').wrappers[index].vm.$emit('input', option);
      await w.vm.$forceUpdate();

      expect(w.vm.$props.config.features[index]).toBe(option);
      expect(emit).toHaveBeenCalledWith(COMMIT);
      emit.mockClear();
    }

    for (let index = 0; index < w.findAll('.feature-selector').wrappers.length; index++) {
      for (const option of OPTIONS) {
        await _test(index, option);
      }
    }
  });

  test('remove specific', async () => {
    // start out with a feature for every option
    var FEATURES = clone(OPTIONS);
    const w = factory({
      ...CONFIG,
      features: clone(OPTIONS),
      feature_parameters: OPTIONS.map(v => DEFAULTS[v])
    });

    async function _test(index) {
      // remove a feature
      await w.findAll('.remove-button').wrappers[index].trigger('click');

      // make sure the right features are still there
      FEATURES.splice(index, 1);
      expect(w.vm.$props.config.features).toStrictEqual(FEATURES);

      w.destroy();
    }

    for (let i = 0; i < OPTIONS.length; i++) {
      await _test(i);
    }
  });

  test('render parameters', async () => {
    // start out with a feature for every option
    const w = factory({
      ...CONFIG,
      features: clone(OPTIONS),
      feature_parameters: OPTIONS.map(v => DEFAULTS[v])
    });
    w.vm.$forceUpdate();

    async function _test(index) {
      const feature = OPTIONS[index]
      const pars = Object.keys(w.vm.$props.config.feature_parameters[index]);
      // if feature has parameters
      if (!isEmpty(pars)) {
        const row = w.findAll('.feature-row').wrappers[index];
        const labels = row.findAll('.parameter-label').wrappers;
        const fields = row.findAll('.parameter-field').wrappers;

        // should have a label and a field for every parameter
        expect(labels.length).toBe(pars.length);
        expect(fields.length).toBe(pars.length);

        for (let i = 0; i < pars.length; i++) {
          expect(labels[i].text()).toBe(PARAMETERS[feature][pars[i]].description);
          expect(fields[i].vm.$props.value).toBe(PARAMETERS[feature][pars[i]].default);
        }
      }
    }

    for (let i = 0; i < OPTIONS.length; i++) {
      await _test(i);
    }
  });

  test('set parameters', async () => {
    // start out with a feature for every option
    const w = factory({
      ...CONFIG,
      features: clone(OPTIONS),
      feature_parameters: OPTIONS.map(v => DEFAULTS[v])
    });
    emit = jest.spyOn(w.vm, '$emit');
    w.vm.$forceUpdate();

    async function _test(index) {
      const feature = OPTIONS[index]
      const pars = Object.keys(w.vm.$props.config.feature_parameters[index]);
      // if feature has parameters
      if (!isEmpty(pars)) {
        const fields = w.findAllComponents(SchemaField).wrappers;

        for (let i = 0; i < pars.length; i++) {
          w.vm.$props.config.feature_parameters[index][pars[i]] = undefined;
          w.vm.$forceUpdate();

          expect(fields[i].value).toBe(undefined);
          // todo: ideally this should get flagged ~ validation

          await fields[i].vm.$emit(COMMIT, PARAMETERS[feature][pars[i]].default);
          await flushPromises;
          w.vm.$forceUpdate();

          expect(w.vm.$props.config.feature_parameters[index][pars[i]]).toBe(PARAMETERS[feature][pars[i]].default)
          expect(emit).toHaveBeenCalledWith(COMMIT);
          emit.mockClear();
        }
      }
    }

    for (let i = 0; i < OPTIONS.length; i++) {
      await _test(i);
    }
  });
});

describe('output', () => {
  var w;
  var emit;

  var inputs;
  var selectors;
  var checkboxes;

  beforeEach(async () => {
    const OPTIONS = store.getters['schemas/getFeature'].options;
    const DEFAULTS = store.getters['schemas/getFeature'].defaults;

    w = factory({
      ...CONFIG,
      features: clone(OPTIONS),
      feature_parameters: OPTIONS.map(v => DEFAULTS[v])
    });
    await flushPromises();
    await w.vm.$nextTick();

    emit = jest.spyOn(w.vm, '$emit');

    inputs = w.findAllComponents(BFormInput).wrappers;
    selectors = w.findAllComponents(BFormSelect).wrappers;
    checkboxes = w.findAllComponents(BFormCheckbox).wrappers;
  });

  test('focusOut -> commit', async () => {
    for (const input of inputs) {
      expect(input.exists()).toBeTruthy();
      console.log(input.classes());

      // mock a value change & emit focusout
      input.setProps({ value: undefined });
      input.vm.$parent.$data.valueOut = undefined;  // pass this.valueOut !== this.value check in SchemaField
      await input.vm.$emit('focusout');

      expect(emit).toHaveBeenCalledWith(COMMIT);
      emit.mockClear();
    }
  });

  test('keyUp Enter -> commit', async () => {
    for (const input of inputs) {
      expect(input.exists()).toBeTruthy();
      console.log(input.classes());

      // mock a value change & emit keyup Enter
      input.setProps({ value: undefined });
      input.vm.$parent.$data.valueOut = undefined;  // pass this.valueOut !== this.value check in SchemaField
      await input.trigger('keyup.enter');

      expect(emit).toHaveBeenCalledWith(COMMIT);
      emit.mockClear();
    }
  });

  test('change -> commit', async () => {
    for (const field of [ ...selectors, ...checkboxes ]) {
      expect(field.exists()).toBeTruthy();
      console.log(field.classes());

      // mock a value change & emit keyup Enter
      field.setProps({ value: undefined });
      field.vm.$parent.$data.valueOut = undefined;  // pass this.valueOut !== this.value check in SchemaField
      await field.trigger('change');

      expect(emit).toHaveBeenCalledWith(COMMIT);
      emit.mockClear();
    }
  });

  test('validate -> valid', async () => {
    w.setData({ validVideo: null, validDesign: null })
    axios_put.mockResolvedValueOnce({  // mock check_video_path
      status: 200, data: true
    });
    axios_put.mockResolvedValueOnce({  // mock check_design_path
      status: 200, data: true
    });

    const valid = await w.vm.isValid();
    expect(valid).toBe(true);
  });

  test('validate -> invalid files -> invalid', async () => {
    w.setData({ validVideo: null, validDesign: null })
    axios_put.mockResolvedValue({  // mock check_video_path & check_design_path
      status: 200, data: false
    });

    const valid = await w.vm.isValid();
    expect(valid).toBe(false);
  });

  test('validate -> no features -> invalid', async () => {
    w.setProps({ config: { ...CONFIG, features: [], feature_parameters: [] }})
    w.setData({ validVideo: null, validDesign: null })
    axios_put.mockResolvedValue({  // mock check_video_path & check_design_path
      status: 200, data: true
    });

    const valid = await w.vm.isValid();
    expect(valid).toBe(false);
    expect(w.find('.add-button').classes()).toContain('is-invalid');
  });

  test('return config', async () => {
    const config = await w.vm.getConfig();
    expect(config).toMatchObject(w.vm.$props.config);
  });
});
