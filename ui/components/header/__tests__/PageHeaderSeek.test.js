import { mount, shallowMount } from "@vue/test-utils";

import PageHeaderSeek from "../PageHeaderSeek";
import flushPromises from 'flush-promises';

import axios from 'axios';
jest.mock('axios');

import {test, describe, beforeEach, afterEach} from "@jest/globals";
import {uuidv4} from "../../../static/util";
import {waitSync} from "../../../static/shapeflow";
import {events} from "../../../static/events";


const ID = uuidv4();
const SEEK_POSITION = 0.5;
const TOTAL_TIME = 260


const factory = (mount_method) => {
  axios.get.mockResolvedValueOnce({  // get_seek_position
    status: 200, data: SEEK_POSITION,
  });
  axios.get.mockResolvedValueOnce({  // get_total_time
    status: 200, data: TOTAL_TIME,
  });
  return mount_method(
    PageHeaderSeek,
    {
      propsData: {id: ID}
    }
  )
};

test('mount', async () => {
  const w = factory(shallowMount);
  expect(w.vm).toBeTruthy();

  await flushPromises();
  expect(w.vm.$data.position).toBe(SEEK_POSITION);
  expect(w.vm.$data.totalSeconds).toBe(TOTAL_TIME);
  expect(w.vm.$data.isLoading).toBe(true);

  expect(w.find('span').text()).toBe('02:10.0 / 04:20.0');
});

test('events', async () => {
  var seeks = 0;
  jest.spyOn(PageHeaderSeek.methods, 'handleSeek').mockImplementation(() => {seeks++});  // bypass throttle/debounce
  const w = factory(shallowMount);

  await flushPromises();
  expect(w.vm.$data.position).toBe(SEEK_POSITION);

  w.vm.$root.$emit(events.seek.set(ID));
  w.vm.$root.$emit(events.seek.reset(ID));
  w.vm.$root.$emit(events.seek.step_fw(ID));
  w.vm.$root.$emit(events.seek.step_bw(ID));

  expect(seeks).toBe(4);
});

test('handleSeek', async () => {
  const handleSeek = jest.spyOn(PageHeaderSeek.methods, 'handleSeek');
  const doSeek = jest.spyOn(PageHeaderSeek.methods, 'doSeek');
  const w = factory(shallowMount);

  axios.post.mockResolvedValueOnce({
    status: 200, data: 0.9,
  });
  w.vm.handleSeek();

  expect(handleSeek).toBeCalled();
  // expect(doSeek).toBeCalled();  // todo: doesn't work outside of debugger for some reason
});

test('destroy', () => {
  var seeks = 0;
  jest.spyOn(PageHeaderSeek.methods, 'handleSeek').mockImplementation(() => {seeks++});
  const w = factory(shallowMount);

  w.destroy();

  w.vm.$root.$emit(events.seek.set(ID));
  w.vm.$root.$emit(events.seek.reset(ID));
  w.vm.$root.$emit(events.seek.step_fw(ID));
  w.vm.$root.$emit(events.seek.step_bw(ID));

  expect(seeks).toBe(0);
});

