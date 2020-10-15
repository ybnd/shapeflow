import {mount} from "@vue/test-utils";
import {describe, test} from "@jest/globals";

import {BFormCheckbox, BFormGroup, BFormInput, BFormRow, BFormSelect, BInputGroup, BRow} from "bootstrap-vue";

import SchemaCategory from "../SchemaCategory";
import SchemaDefinition from "../SchemaDefinition";
import SchemaField from "../SchemaField";
import {COMMIT} from "../../../static/events";
import {startServer, killServer} from "../../../static/shapeflow";
import {get_schemas, get_settings, normalize_config} from "../../../static/api";
import { readFileSync } from "fs";
import SchemaForm from "../SchemaForm";


var SCHEMAS;
var SETTINGS;
var CONFIG;


beforeAll(async () => {
  startServer();

  async function _retry_once(method, arg) {
    return method(arg).then(out => {
      return out;
    }).catch(() => {
      return method(arg).then(out => {
        return out;
      })
    })
  }

  SCHEMAS = await _retry_once(get_schemas);
  SETTINGS = await _retry_once(get_settings);

  CONFIG = await _retry_once(normalize_config, JSON.parse(readFileSync(__dirname + '/config.json')));

  killServer();
});

const CONFIG_SKIP = [  // todo: these are skipped in pages/analysis/configure
  'name', // handled separately; also applies to masks[*].name, which shouldn't be changed
  'description', // handled separately
  'features', // handled by BasicConfig.vue
  'feature_parameters', // handled by BasicConfig.vue
  'frame_interval_setting', // handled by BasicConfig.vue
  'dt', // handled by BasicConfig.vue
  'Nf', // handled by BasicConfig.vue
  'design_path', // handled by BasicConfig.vue
  'video_path', // handled by BasicConfig.vue
];


function factory(
  data, schema, skip = [],
  { property_as_title = false, class_ = "" } = {}
) {
  return mount(SchemaForm, {
    propsData: { data, schema, skip, class: class_, property_as_title },
    stubs: {
      SchemaForm,
      SchemaCategory,
      SchemaDefinition,
      SchemaField,
      'b-row': BRow,
      'b-form-row': BFormRow,
      'b-form-group': BFormGroup,
      'b-input-group': BInputGroup,
      'b-form-select': BFormSelect,
      'b-form-input': BFormInput,
      'b-form-checkbox': BFormCheckbox,
    }
  });

}



describe('settings', () => {
  test('mount', () => {
    const w = factory(SETTINGS, SCHEMAS.settings);
  });

  test('undefined -> throw', () => {
    expect(() => { factory(undefined, undefined) }).toThrow();
    expect(() => { factory(undefined, SCHEMAS.settings) }).toThrow();
    expect(() => { factory(SETTINGS, undefined) }).toThrow();
  });
});

describe('config', () => {
  test('mount', () => {
    const w = factory(CONFIG, SCHEMAS.config, CONFIG_SKIP, { property_as_title: true });
  });

  test('undefined -> throw', () => {
    expect(() => { factory(undefined, undefined) }).toThrow();
    expect(() => { factory(undefined, SCHEMAS.config) }).toThrow();
    expect(() => { factory(SETTINGS, undefined) }).toThrow();
  });
});

test('mismatched data/schema -> throw', () => {
  expect(() => { factory(CONFIG, SCHEMAS.settings, CONFIG_SKIP) }).toThrow();
  expect(() => { factory(SETTINGS, SCHEMAS.config, CONFIG_SKIP, { property_as_title: true }) }).toThrow();
});
