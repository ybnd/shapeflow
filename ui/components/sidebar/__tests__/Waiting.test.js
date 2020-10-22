import { shallowMount} from "@vue/test-utils";
import {afterEach, beforeEach, test} from "@jest/globals";

import Waiting from '../Waiting';

const PERIOD = 10;
const WAIT_FOR = 100;

// Waiting.advance gets called once on mount and runs through Waiting.frames once per period
const CALLS = 1 + Math.round(WAIT_FOR / PERIOD * Waiting.data().frames.length);

function factory() {
  return shallowMount(
    Waiting, {
      propsData: {
        period: PERIOD,
      },
    },
  )
}

const advance = jest.spyOn(Waiting.methods, 'advance');

beforeEach(() => {
  jest.useFakeTimers();
  advance.mockClear();
});

afterEach(() => {
  jest.clearAllTimers();
  advance.mockClear();
});

test('mount', () => {
  expect(advance).toHaveBeenCalledTimes(0);
  const w = factory();

  // Let Waiting.interval run for a bit
  jest.advanceTimersByTime(WAIT_FOR);

  // Waiting.advance gets called once on mount and runs through Waiting.frames once per period
  expect(advance).toHaveBeenCalledTimes(CALLS);
});

test('destroy', async () => {
  expect(advance).toHaveBeenCalledTimes(0);
  const w = factory();

  // let Waiting.interval run for a bit
  jest.advanceTimersByTime(WAIT_FOR);

  // Waiting.advance gets called once on mount and runs through Waiting.frames once per period
  expect(advance).toHaveBeenCalledTimes(CALLS);

  // destroy Waiting instance
  await w.destroy();

  // let Waiting.interval run some more
  jest.advanceTimersByTime(WAIT_FOR);

  // Number of calls should stay the same
  expect(advance).toHaveBeenCalledTimes(CALLS);
});
