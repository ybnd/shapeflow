import {createLocalVue, shallowMount} from "@vue/test-utils"
import {beforeEach, describe, test} from "@jest/globals";
import Vuex from "vuex";

import Default from '../default'
import Sidebar from "../../components/sidebar/Sidebar";
import NoticeBox from "../../components/notice/NoticeBox";

var localVue;
var store;

const schemas_sync = jest.fn();
const settings_sync = jest.fn();
const analyzers_loop = jest.fn();
const analyzers_stop = jest.fn();

navigator.sendBeacon = jest.fn();
const checkIfTooSmall = jest.spyOn(Default.methods, 'checkIfTooSmall');

beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex);

  store = new Vuex.Store({
    modules: {
      schemas: {
        namespaced: true,
        actions: {
          sync: schemas_sync,
        }
      },
      settings: {
        namespaced: true,
        actions: {
          sync: settings_sync,
        }
      },
      analyzers: {
        namespaced: true,
        actions: {
          loop: analyzers_loop,
          stop: analyzers_stop,
        }
      },
    }
  })
})

afterEach(() => {
  jest.clearAllMocks();
})

function factory() {
  return shallowMount(Default, {
    mocks: { $store: store },
    stubs: {
      Sidebar,
      NoticeBox,
      'nuxt': { template: '<div class="nuxt" />' },
    },
    localVue,
  })
}

test('mount & destroy', () => {
  const w = factory();

  const app_body = w.find('.app-body');
  const sidebar = w.findComponent(Sidebar);
  const noticebox = w.findComponent(NoticeBox);
  const nuxt = w.find('.nuxt');
  const msg = w.find('.too-small-message');

  expect(app_body.isVisible()).toBe(true);

  expect(sidebar.exists()).toBe(true);
  expect(noticebox.exists()).toBe(true);
  expect(nuxt.exists()).toBe(true);

  expect(msg.exists()).toBe(false);
  expect(w.vm.$data.tooSmall).toBe(false);

  w.destroy();
});

test('unload', async () => {
  const w = factory();

  expect(navigator.sendBeacon).toHaveBeenCalledTimes(0);
  await window.dispatchEvent(new Event('unload'));
  expect(navigator.sendBeacon).toHaveBeenCalledTimes(1)
});

describe('resize', () => {
  test('large enough', async () => {
    const w = factory();

    const app_body = w.find('.app-body');
    const msg = w.find('.too-small-message');

    expect(app_body.isVisible()).toBe(true);
    expect(msg.exists()).toBe(false);

    expect(checkIfTooSmall).not.toHaveBeenCalled();

    // default window is 1024x768
    await window.dispatchEvent(new Event('resize'));

    expect(checkIfTooSmall).toHaveBeenCalled();
    expect(w.vm.$data.tooSmall).toBe(false);

    expect(app_body.isVisible()).toBe(true);
    expect(msg.exists()).toBe(false);
  });

  test('too small', async () => {
    const w = factory();

    const app_body = w.find('.app-body');

    expect(app_body.isVisible()).toBe(true);
    expect(w.find('.too-small-message').exists()).toBe(false);

    expect(checkIfTooSmall).not.toHaveBeenCalled()

    // default window is 1024x768
    window.innerWidth = 256;
    window.innerHeight = 192;
    await window.dispatchEvent(new Event('resize'));

    expect(checkIfTooSmall).toHaveBeenCalled();
    expect(w.vm.$data.tooSmall).toBe(true);

    expect(app_body.isVisible()).toBe(false);
    expect(w.find('.too-small-message').exists()).toBe(true);
  });
});
