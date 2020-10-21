import {mount} from "@vue/test-utils";
import {afterAll, afterEach, beforeEach, describe, test} from "@jest/globals";
import {cloneDeep} from 'lodash';
import {BButton, BFormInput, BInputGroup, BPopover, BTbody} from "bootstrap-vue";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

import log from '../log';
import {splitlines} from "../../src/util";
import {waitSync} from "../../src/shapeflow";


const LOG = 'example log line\nand another line\nand ANOTHER line again\nand so on\n';
const FILTER = 'another';

function factory() {
  return mount(log, {
    stubs: {
      PageHeader,
      PageHeaderItem,
      'b-button': BButton,
      'b-popover': BPopover,
      'b-tbody': BTbody,
      'b-input-group': BInputGroup,
      'b-form-input': BFormInput,
    }
  });
}

// keep a copy of the originals
const og_document = cloneDeep(document)
const og_window = cloneDeep(window);

window.XMLHttpRequest = jest.fn(() => {
  const _map = {};
  return {
    open: jest.fn(),
    send: jest.fn(),
    sendRequestHeader: jest.fn(),
    responseText: undefined,
    _map: _map,
    addEventListener: jest.fn((event, listener) => {
      _map[event] = listener
    }),
    dispatchEvent: jest.fn((event, payload) => {
      _map[event](payload);
    }),
  };
});

beforeEach(() => {
  jest.useFakeTimers();
})

afterEach(() => {
  jest.clearAllMocks();
  jest.clearAllTimers();
});

test('mount & destroy', () => {
  const w = factory();

  // There should be a header with 3 items
  expect(w.findComponent(PageHeader).exists()).toBeTruthy();
  expect(w.findAllComponents(PageHeaderItem).wrappers).toHaveLength(3);

  // There should be 2 buttons
  expect(w.find('.log-follow').exists()).toBeTruthy();
  expect(w.find('.log-case-sensitive').exists()).toBeTruthy();

  //There should be a filter field
  expect(w.findComponent(BFormInput).classes()).toContain('log-filter-field');

  // There should be a log table
  expect(w.find('.log-table').exists()).toBeTruthy()

  // should have made a request
  const request = w.vm.$data.request;
  expect(request).toBeTruthy();
  expect(request.open).toHaveBeenCalled();
  expect(request.send).toHaveBeenCalled();
  expect(request._map['progress']).toBeTruthy();

  w.destroy();
});

describe('scrolling', () => {
  var w;
  var scrollNow;

  function fake(element, property, value) {
    return {
      ...element,
      [property]: value,
    }
  }

  beforeEach(() => {
    scrollNow = jest.spyOn(log.methods, 'scrollNow');
    w = factory();

    // simulate element geometry
    w.vm.$refs.view = fake(w.vm.$refs.view, 'clientHeight', 300);
    w.vm.$refs.log = fake(w.vm.$refs.log, 'clientHeight', 1000);
  });

  test('scrolled up/left (resting position)', async () => {
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollTop', 0);
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollLeft', 0);

    expect(w.vm.scroll.isScrolled).toBe(false);
  });

  test('scrolled down/left (follow position)', async () => {
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollTop', 730);  // within tolerance
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollLeft', 20);  // within tolerance

    expect(w.vm.scroll.isScrolled).toBe(true);
  });

  test('scroll down', async () => {
    // start out scrolled somewhere in the middle
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollTop', 400);
    w.vm.$refs.log.$el = fake(w.vm.$refs.log.$el, 'scrollLeft', 90);

    expect(w.vm.scroll.isScrolled).toBe(false);

    await w.vm.scrollNow();

    // should be scrolled down now
    expect(w.vm.scroll.isScrolled).toBe(false);
  });

  test('no follow', async () => {
    w.setData({ follow: false, release: false })

    // wait for the interval to initialize
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).not.toHaveBeenCalled();

    // scrollNow is called 10x per second
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).not.toHaveBeenCalled();
  });

  test('follow', async () => {
    w.setData({ follow: true, release: false })

    // wait for the interval to initialize
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).not.toHaveBeenCalled();

    // scrollNow is called 10x per second
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).toHaveBeenCalledTimes(10);
  });

  test('follow & release', async () => {
    w.setData({ follow: true, release: false })

    // wait for the interval to initialize
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).not.toHaveBeenCalled();

    // queue up a scroll event
    setTimeout(
      () => { w.find('.log-table').trigger('scroll') },
      150
    );

    // scrollNow is called 10x per second
    await jest.advanceTimersByTime(1000);
    expect(scrollNow).toHaveBeenCalled()
    expect(scrollNow.mock.calls.length).toBeLessThan(10);
  });
});

describe('controls', () => {
  test('follow', async () => {
    const scrollNow = jest.spyOn(log.methods, 'scrollNow');
    // not following by default
    const w = factory();


    await w.find('.log-follow').trigger('click');
    expect(scrollNow).toHaveBeenCalled();
  });

  test('filter', async () => {
    // not filtering by default by default
    const handleSetFilter = jest.spyOn(log.methods, 'handleSetFilter');
    const filterLog = jest.spyOn(log.methods, 'filterLog');
    const w = factory();

    await w.find('.log-filter-field').vm.$emit('input');
    expect(handleSetFilter).toHaveBeenCalled();
    // expect(filterLog).toHaveBeenCalled();  // todo: can't get past debouncer :(
  });

  test('case sensitive', async () => {
    // not filtering by default by default
    const filterLog = jest.spyOn(log.methods, 'filterLog');
    const w = factory();

    await w.find('.log-case-sensitive').trigger('click');
    expect(filterLog).toHaveBeenCalled();
  });
});

describe('handle log data', () => {
  test('receive log on progress', async () => {
    const w = factory();
    const handleLogText = jest.spyOn(w.vm, 'handleLogText');
    const filterLog = jest.spyOn(w.vm, 'filterLog');

    await w.vm.$data.request.dispatchEvent('progress', { target: { responseText: LOG }});

    expect(handleLogText).toHaveBeenCalled();
    expect(filterLog).toHaveBeenCalled();
    expect(w.vm.$data.log).toBe(LOG);
    expect(w.vm.$data.filtered_lines).toStrictEqual(splitlines(LOG));
  });

  test('scroll down if following', async () => {
    const w = factory();

    w.setData({ follow: true });
    w.vm.scroll = jest.fn().mockReturnValue({ isScrolled: false });
    w.vm.scrollNow = jest.fn();

    await w.vm.$data.request.dispatchEvent('progress', { target: { responseText: LOG }});

    expect(w.vm.scrollNow).toHaveBeenCalled();
  });

  test('filter (case insensitive)', async () => {
    const w = factory();

    w.vm.$data.filter = FILTER;
    w.vm.$data.case_sensitive = false;

    await w.vm.$data.request.dispatchEvent('progress', { target: { responseText: LOG }});

    expect(w.vm.$data.log).toBe(LOG);
    expect(w.vm.$data.filtered_lines).toStrictEqual(splitlines('and another line\nand ANOTHER line again'));
  });

  test('filter (case sensitive)', async () => {
    const w = factory();

    w.vm.$data.filter = FILTER;
    w.vm.$data.case_sensitive = true;

    await w.vm.$data.request.dispatchEvent('progress', { target: { responseText: LOG }});

    expect(w.vm.$data.log).toBe(LOG);
    expect(w.vm.$data.filtered_lines).toStrictEqual(splitlines('and another line'));
  });
});


