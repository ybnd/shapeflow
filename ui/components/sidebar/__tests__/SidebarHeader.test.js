import {createLocalVue, shallowMount} from "@vue/test-utils";
import {afterEach, beforeEach, test} from "@jest/globals";

import SidebarHeader from "../SidebarHeader";
import VueRouter from "vue-router";


var localVue;


function factory (url = URL) {
  localVue = createLocalVue();
  localVue.use(VueRouter)
  const router = new VueRouter();

  return shallowMount(SidebarHeader, {
    propsData: {},
    localVue,
    router,
  });
}

test('click to go home', async () => {
  const w = factory();
  w.vm.$router.push = jest.fn();

  await w.find('.home').trigger('click');
  expect(w.vm.$router.push).toHaveBeenCalled();
  expect(w.vm.$router.push).toHaveBeenCalledWith('/')
});
