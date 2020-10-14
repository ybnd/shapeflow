import {createLocalVue, shallowMount} from "@vue/test-utils";
import {events} from "../../../static/events";
import {waitSync} from "../../../static/shapeflow";
import flushPromises from "flush-promises";
import axios from 'axios';
import VueRouter from "vue-router";
import SidebarNavDropdown from "../SidebarNavDropdown";

const NAME = 'dropdown';
const ICON = 'some-icon-class';

function factory (url = URL) {
  return shallowMount(SidebarNavDropdown, {
    propsData: { name: NAME, icon: ICON},
  })
}

test('mount', () => {
  const w = factory();

  expect(w.find('.nav-link').text()).toBe(NAME);
  expect(w.find('i').element.className).toContain(ICON);
});

test('click', async () => {
  const w = factory();

  // **not** open by default
  expect(w.find('.nav-dropdown').classes()).not.toContain('open');

  await w.find('.nav-dropdown-toggle').trigger('click');
  expect(w.find('.nav-dropdown').classes()).toContain('open');
});

