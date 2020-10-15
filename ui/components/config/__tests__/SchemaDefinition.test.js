import {mount} from "@vue/test-utils";
import {describe, test} from "@jest/globals";

import {BFormCheckbox, BFormInput, BFormRow, BFormSelect, BFormGroup} from "bootstrap-vue";

import SchemaDefinition from "../SchemaDefinition";
import SchemaField from "../SchemaField";
import {COMMIT} from "../../../static/events";


const def = SchemaDefinition.data().def;
const MODELS_MATCH = {
  [def.COO]: { x: 15, y: 32 },
  [def.HSVCOLOR]: { h: 120, s: 200, v: 210 },
  [def.FLIPCONFIG]: { horizontal: true, vertical: false},
}
const MODELS_MISMATCH = {
  [def.COO]: { x: 15 },
  [def.HSVCOLOR]: { r: 25, g:23, b: 89 },
  [def.FLIPCONFIG]: { horizontal: false, vetrical: true },
}
const SET_0_TO = {
  [def.COO]: 20,
  [def.HSVCOLOR]: 60,
  [def.FLIPCONFIG]: true,
};
const TITLE = 'test-definition';

function factory (definition = undefined, model = undefined) {
  return mount(SchemaDefinition, {
    propsData: { title: TITLE, model: model, definition: definition },
    stubs: {
      SchemaField,
      'b-form-row': BFormRow,
      'b-form-group': BFormGroup,
      'b-form-select': BFormSelect,
      'b-form-input': BFormInput,
      'b-form-checkbox': BFormCheckbox,
    },
  })
}

test('definition undefined -> throw', () => {
  expect(factory).toThrow()
});

for (const DEF of Object.values(def)) {
  const MATCH = MODELS_MATCH[DEF];
  const MISMATCH = MODELS_MISMATCH[DEF];

  describe(DEF, () => {
    test('model matches -> mounts properly', () => {
      const w = factory(DEF, MATCH);

      // there should be one SchemaField for every field in fields[DEF]
      const fields = w.findAllComponents(SchemaField).wrappers;
      expect(fields.length).toBe(SchemaDefinition.data().fields[DEF].length);

      // the title should be in the first label
      const labels = w.findAll('label').wrappers;
      expect(labels[0].text()).toContain(TITLE);
    });

    test('model undefined -> only a label', () => {
      const w = factory(DEF);

      // no fields
      const fields = w.findAllComponents(SchemaField).wrappers;
      expect(fields.length).toBe(0);

      // a single label with the title
      const labels = w.findAll('label').wrappers;
      expect(labels.length).toBe(1);
      expect(labels[0].text()).toContain(TITLE);
    });

    test('model mismatches -> empty div', () => {
      const w = factory(DEF, MISMATCH);

      // no fields
      const fields = w.findAllComponents(SchemaField).wrappers;
      expect(fields.length).toBe(0);

      // no labels
      const labels = w.findAll('label').wrappers;
      expect(labels.length).toBe(0);

      // no nothing
      expect(w.vm.$children.length).toBe(0);
    });

    test('re-emit commit events', async () => {
      const w = factory(DEF, MATCH);
      w.vm.$emit = jest.fn();

      const field = w.findComponent(SchemaField);

      await field.vm.$emit(COMMIT, SET_0_TO[DEF]);  // VueWrapper.trigger() doesn't work with custom events
      expect(w.vm.$emit).toHaveBeenCalledWith(COMMIT)
    });
  });
}
