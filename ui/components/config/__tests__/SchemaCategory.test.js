import {shallowMount} from "@vue/test-utils";
import {test} from "@jest/globals";

import SchemaCategory from "../SchemaCategory";
import flushPromises from "flush-promises";
import {BFormGroup} from "bootstrap-vue";

const TITLE = 'some category'

function factory ({ open = true, emit_toggle = false, clickable = true } = {}) {
  return shallowMount(SchemaCategory, {
    propsData: { title: TITLE, open, emit_toggle, clickable },
    stubs: {
      'b-form-group': BFormGroup,
    },
  })
}

test('mount', async () => {
  const w = factory();
  w.vm.$emit = jest.fn();

  const summary = w.find('summary');
  const details = w.find('details');

  expect(summary.exists()).toBeTruthy();
  expect(details.exists()).toBeTruthy();

  expect(summary.text()).toBe(TITLE);

  await details.trigger('toggle');

  expect(w.vm.$emit).not.toHaveBeenCalled();
});

test('re-emit details toggle events', async () => {
  const w = factory({emit_toggle: true});
  w.vm.$emit = jest.fn();

  const details = w.find('details');
  await details.trigger('toggle');

  expect(w.vm.$emit).toHaveBeenCalledWith('toggle');
});
