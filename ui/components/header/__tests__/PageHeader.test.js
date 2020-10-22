import { mount, shallowMount } from "@vue/test-utils";

import PageHeader from "../PageHeader";
import PageHeaderItem from "../PageHeaderItem";

import {test, describe, beforeEach, afterEach} from "@jest/globals";
import axios from "axios";


const factory = () => {
  return mount(
    PageHeader, {
      slots: {
        default: [
          '<PageHeaderItem><h1>first item</h1></PageHeaderItem>',
          '<PageHeaderItem><p>second item</p></PageHeaderItem>',
          '<PageHeaderItem><span>third item</span></PageHeaderItem>'
        ]
      },
      stubs: {
        PageHeaderItem: PageHeaderItem,
      }
    }
  )
};


test('mount', () => {
  const w = factory();
  expect(w.vm).toBeTruthy();

  expect(w.find('h1').text()).toBe('first item');
  expect(w.find('p').text()).toBe('second item');
  expect(w.find('span').text()).toBe('third item');
});
