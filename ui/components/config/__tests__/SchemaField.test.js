import {mount} from "@vue/test-utils";
import {describe, test} from "@jest/globals";

import {BFormCheckbox, BFormInput, BFormRow, BFormSelect} from "bootstrap-vue";

import SchemaField from "../SchemaField";
import {COMMIT} from "../../../src/events";

const CLASS_ = 'dummy-class';
const TITLE = 'test-field';

const types = SchemaField.data().types_;  // todo: maybe in a separate .js file?

const VALUE = {
  [types.ENUM]: 'A',
  [types.STRING]: 'a string',
  [types.PATH]: '/some/path',
  [types.INTEGER]: 10,
  [types.FLOAT]: 3.14,
  [types.NUMBER]: 6.28,
  [types.BOOLEAN]: false,
}
const SET_TO = {
  [types.ENUM]: 'B',
  [types.STRING]: 'another string',
  [types.PATH]: '/some/other/path',
  [types.INTEGER]: 100,
  [types.FLOAT]: 0.0,
  [types.NUMBER]: 0.0,
  [types.BOOLEAN]: true,
}
const STYLE_ = {
  'background-color': 'red',
};

function factory(
  { type = undefined, value = undefined,
    title = TITLE, options, style_ , class_, new_row }
  ) {
  return mount(SchemaField, {
    propsData: { type, value, title, options, style_, class_, new_row, },
    stubs: {
      'b-form-row': BFormRow,
      'b-form-select': BFormSelect,
      'b-form-input': BFormInput,
      'b-form-checkbox': BFormCheckbox,
    },
  });
}

test('throw if no type specified', () => {
  expect(factory).toThrow();
});

for (const TYPE in SchemaField.data().types) {
  describe(`type = ${TYPE}`, () => {
    test('throw if no value specified', () => {
      expect(() => {
        const w = factory({ type: TYPE })
      }).toThrow();
    });

    test('mount', () => {
      const w = factory({type: TYPE, value: VALUE[TYPE]});

      // should be on a new row by default
      expect(w.props().new_row).toBe(true);
      expect(w.classes()).toContain('form-row');

      // should have a label
      const label = w.find('label');
      expect(label.exists()).toBeTruthy();
      expect(label.text()).toBe(TITLE);

      // should have a field with value === VALUE[TYPE]
      const field = w.find('.field');
      expect(field.exists()).toBeTruthy();
      expect(w.vm.$props.value).toBe(VALUE[TYPE]);
      expect(w.vm.$data.valueOut).toBe(VALUE[TYPE]);

      try {
        expect(field.vm.$props.value).toBe(VALUE[TYPE]);
      } catch(error) {
        // <b-form-checkbox/> has value="true" by default for some reason
        expect(TYPE).toBe("boolean");
      }
    });

    test('mount -> empty title', () => {
      const w = factory({ type: TYPE, value: VALUE[TYPE], title: '' });

      try {
        // there should be no label
        expect(w.find('label').exists()).toBeFalsy();
      } catch(error) {
        // <b-form-checkbox/> renders a label by default, we can rule out that we're dealing with that
        expect(w.find('label').classes()).toContain('custom-control-label');
      }
    });

    test('mount -> not on a new row', () => {
      const w = factory({ type: TYPE, value: VALUE[TYPE], new_row: false });

      expect(w.props().new_row).toBe(false);
      expect(w.classes()).not.toContain('form-row');
    });

    test('set field class', () => {
      const w = factory({ type: TYPE, value: VALUE[TYPE], class_: CLASS_ });

      const field = w.find('.field');
      expect(field.classes()).toContain(CLASS_)
    });

    test('set field style', () => {
      const w = factory({ type: TYPE, value: VALUE[TYPE], style_: STYLE_ });

      const field = w.find('.field');
      expect(field.element.style).toMatchObject(STYLE_);
    });

    test('follow changing value', async () => {
      const w = factory({type: TYPE, value: VALUE[TYPE]});
      const parse = jest.spyOn(w.vm.$data.parse, TYPE);

      expect(w.vm.$data.valueOut).toBe(VALUE[TYPE]);

      w.vm.field = SET_TO[TYPE];

      expect(w.vm.$data.valueOut).toBe(SET_TO[TYPE]);
      expect(parse).toHaveBeenCalled();
      expect(parse).toHaveBeenCalledWith(SET_TO[TYPE]);
    });

    describe('changed value', () => {
      test('no further input -> no events', () => {
        const w = factory({type: TYPE, value: VALUE[TYPE]});
        w.vm.$emit = jest.fn();

        expect(w.vm.$data.valueOut).toBe(VALUE[TYPE]);
        w.vm.field = SET_TO[TYPE];
        expect(w.vm.$data.valueOut).toBe(SET_TO[TYPE]);

        expect(w.vm.$emit).not.toHaveBeenCalledWith(COMMIT, SET_TO[TYPE]);
      });

      if ( [ types.ENUM, types.BOOLEAN ].includes(TYPE) ) {
        test('change -> emit commit event', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          await w.find('.field').trigger('change', SET_TO[TYPE]);
          // expect(w.vm.$emit).toHaveBeenCalledWith(COMMIT, SET_TO[TYPE]);  // todo: can't provide @change v ~ trigger()
        });
      } else {
        test('keyUp Enter -> emit commit event', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          w.vm.field = SET_TO[TYPE];

          const field = w.find('.field')

          await w.find('.field').trigger('keyup.enter');
          expect(w.vm.$emit).toHaveBeenCalledWith(COMMIT, SET_TO[TYPE]);
        });

        test('focus out -> emit commit event', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          w.vm.field = SET_TO[TYPE];

          await w.find('.field').trigger('focusout');
          expect(w.vm.$emit).toHaveBeenCalledWith(COMMIT, SET_TO[TYPE]);
        });
      }
    });

    describe('same value', () => {
      if ( [ types.ENUM, types.BOOLEAN ].includes(TYPE) ) {
        test('change -> emit nothing', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          await w.find('.field').trigger('change', VALUE[TYPE]);
          // expect(w.vm.$emit).not.toHaveBeenCalled();    // todo: can't provide @change v ~ trigger()
        });
      } else {
        test('keyUp Enter ->  emit nothing', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          w.vm.field = VALUE[TYPE];

          await w.find('.field').trigger('keyup.enter');
          expect(w.vm.$emit).not.toHaveBeenCalled();
        });

        test('focus out ->  emit nothing', async () => {
          const w = factory({type: TYPE, value: VALUE[TYPE]});
          w.vm.$emit = jest.fn();

          w.vm.field = VALUE[TYPE];

          await w.find('.field').trigger('focusout');
          expect(w.vm.$emit).not.toHaveBeenCalled();
        });
      }
    });
  });
}
