import { shallowMount } from "@vue/test-utils";
import PageHeaderSeek from "../PageHeaderSeek";


import {test, describe, beforeEach, afterEach} from "@jest/globals";


describe('shallow', () => {
  const factory = () => {return shallowMount(PageHeaderSeek, {})};

  test('mounts fine', () => {
    const w = factory();
    expect(w.isVueInstance()).toBe(true);
  });
});


