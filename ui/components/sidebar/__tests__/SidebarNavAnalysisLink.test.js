import {createLocalVue, mount} from "@vue/test-utils";
import {afterEach, beforeEach, test, describe} from "@jest/globals";

import SidebarNavAnalysisLink from "../SidebarNavAnalysisLink";

import axios from 'axios';
import VueRouter from "vue-router";
import {events} from "../../../static/events";
import {bPopoverJsDomHack, createContainer, uuidv4} from "../../../static/util";
import {BButton, BPopover} from "bootstrap-vue";


const NAME = 'analysis link';
const URL = '/some/url';
const ID = uuidv4();
const ICON = 'some-icon-class';


function factory (url = URL) {
  const localVue = createLocalVue();
  localVue.use(VueRouter)
  const router = new VueRouter();

  return mount(SidebarNavAnalysisLink, {
    attachTo: createContainer(),
    propsData: { name: NAME, id: url, icon: ICON },
    localVue,
    router,
    stubs: {
      'b-popover': BPopover,
      'b-button': BButton,
    }
  });
}

test('mount', () => {
  const w = factory();

  expect(w.find('.sidebar-analysis-link').text()).toBe(NAME);
  expect(w.find('i').element.className).toContain(ICON)
});

test('events', async () => {
  const w = factory();

  expect(w.find('.sidebar-analysis-link').classes()).not.toContain('highlight');

  await w.vm.$root.$emit(events.sidebar.highlight(URL));
  expect(w.find('.sidebar-analysis-link').classes()).toContain('highlight');

  await w.vm.$root.$emit(events.sidebar.unhighlight(URL));
  expect(w.find('.sidebar-analysis-link').classes()).not.toContain('highlight');

  w.destroy();

  // Events don't arrive anymore
  await w.vm.$root.$emit(events.sidebar.highlight(URL));
  expect(w.find('div').classes()).not.toContain('highlight');
});

test('disable/enable', async () => {
  const w = factory();
  expect(w.find('.sidebar-analysis-link').classes()).not.toContain('disabled');

  await w.setProps({ disabled: true });
  expect(w.find('.sidebar-analysis-link').classes()).toContain('disabled');

  await w.setProps({ enabled: false });
  expect(w.find('.sidebar-analysis-link').classes()).toContain('disabled');

  await w.setProps({ disabled: false });
  expect(w.find('.sidebar-analysis-link').classes()).toContain('disabled');
});

test('click -> api url', async () => {
  axios.post = jest.fn();
  const w = factory('/api/something');
  expect(axios.post).toHaveBeenCalledTimes(0);

  await w.find('.sidebar-analysis-link').trigger('click');
  expect(axios.post).toHaveBeenCalledTimes(1);
});

test('click -> router url', async () => {
  const w = factory('/something');
  w.vm.$router.push = jest.fn();

  await w.find('.sidebar-analysis-link').trigger('click');
  expect(axios.post).toHaveBeenCalledTimes(1);
});

describe('two-stage', () => {
  // For making <b-popover> render properly in JSDOM
  // https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/src/components/popover/popover.spec.js
  const originalCreateRange = document.createRange
  const origGetBCR = Element.prototype.getBoundingClientRect

  beforeEach(bPopoverJsDomHack);

  afterEach(() => {
    // Reset overrides
    document.createRange = originalCreateRange
    Element.prototype.getBoundingClientRect = origGetBCR
  })

  test('click -> confirm', async () => {
    const w = factory(events.sidebar.close(ID));  // two-stage url is handled as an event
    w.vm.$root.$emit = jest.fn();
    expect(w.vm.$root.$emit).not.toHaveBeenCalled();

    var popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).toBe(null);

    await w.find('.sidebar-analysis-link').trigger('click');
    w.vm.$nextTick();

    popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).not.toBe(null);

    const button_confirm = popover.getElementsByClassName('button-confirm')[0];

    console.log(button_confirm)
    await button_confirm.click();

    popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).toBe(null);
    expect(w.vm.$root.$emit).toHaveBeenCalledTimes(2);  // todo: be more specific

    // Note: `w.destroy()` MUST be called at the end of each test in order for
    // the next test to function properly!
    w.destroy();
  });

  test('click -> dismiss', async () => {
    const w = factory(events.sidebar.close(ID));  // two-stage url is handled as an event
    w.vm.$root.$emit = jest.fn();
    expect(w.vm.$root.$emit).not.toHaveBeenCalled();

    var popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).toBe(null);

    await w.find('.sidebar-analysis-link').trigger('click');
    w.vm.$nextTick();

    popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).not.toBe(null);

    const button_confirm = popover.getElementsByClassName('button-dismiss')[0];

    console.log(button_confirm)
    await button_confirm.click();

    popover = document.getElementById(`popover-${events.sidebar.close(ID)}`);
    expect(popover).toBe(null);
    expect(w.vm.$root.$emit).toHaveBeenCalledTimes(1);  // todo: be more specific

    // Note: `w.destroy()` MUST be called at the end of each test in order for
    // the next test to function properly!
    w.destroy();
  });
})
