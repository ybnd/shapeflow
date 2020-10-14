import {createLocalVue, shallowMount} from "@vue/test-utils";
import {afterEach, beforeEach, test} from "@jest/globals";

import SidebarNavLink from "../SidebarNavLink";
import {events} from "../../../static/events";
import {waitSync} from "../../../static/shapeflow";
import flushPromises from "flush-promises";
import axios from 'axios';
import VueRouter from "vue-router";

const NAME = 'link';
const URL = '/some/url';
const ICON = 'some-icon-class';
const CLASSES = 'some other classes';

function factory (url = URL) {
  const localVue = createLocalVue();
  localVue.use(VueRouter)
  const router = new VueRouter();

  return shallowMount(SidebarNavLink, {
    propsData: { name: NAME, url: url, icon: ICON, classes: CLASSES },
    localVue,
    router,
  });
}

test('mount', () => {
  const w = factory();

  expect(w.find('div').text()).toBe(NAME);
  expect(w.find('div').element.className).toContain(CLASSES);
  expect(w.find('i').element.className).toContain(ICON);
});

test('highlight', async () => {
  const w = factory();

  expect(w.vm.$data.highlight).toBe(false);
  expect(w.find('div').classes()).not.toContain('highlight');

  await w.setData({highlight: true});
  expect(w.find('div').classes()).toContain('highlight');
});

test('events', async () => {
  const w = factory();

  expect(w.find('div').classes()).not.toContain('highlight');

  await w.vm.$root.$emit(events.sidebar.highlight(URL));
  expect(w.find('div').classes()).toContain('highlight');

  await w.vm.$root.$emit(events.sidebar.unhighlight(URL));
  expect(w.find('div').classes()).not.toContain('highlight');

  w.destroy();

  // Events don't arrive anymore
  await w.vm.$root.$emit(events.sidebar.highlight(URL));
  expect(w.find('div').classes()).not.toContain('highlight');
});

test('click -> api url', async () => {
  const axios_post = jest.spyOn(axios, 'post');
  const w = factory('/api/something');
  expect(axios_post).toHaveBeenCalledTimes(0);

  await w.find('div').trigger('click');
  expect(axios_post).toHaveBeenCalledTimes(1);
});

test('click -> router url', async () => {
  const w = factory('/something');
  w.vm.$router.push = jest.fn();

  await w.find('div').trigger('click');
  expect(w.vm.$router.push).toHaveBeenCalledTimes(1);
  expect(w.vm.$router.push).toHaveBeenCalledWith('/something');
});
