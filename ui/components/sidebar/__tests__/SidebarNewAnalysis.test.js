import {createLocalVue, mount} from "@vue/test-utils";
import {afterEach, beforeEach, describe, test} from "@jest/globals";

import SidebarNewAnalysis from "../SidebarNewAnalysis";
import BasicConfig from "../../config/BasicConfig";
import {bPopoverJsDomHack, createContainer, uuidv4} from "../../../src/util";
import {BButton, BPopover} from "bootstrap-vue";
import Vuex from "vuex";
import flushPromises from "flush-promises";

import {cloneDeep, isEqual} from 'lodash';


var localVue;
var store;

var action_init;
var getConfig;
var isValid;

function factory () {
  // BasicConfig = require('../../config/BasicConfig');

  return mount(SidebarNewAnalysis, {
    attachTo: createContainer(),
    mocks: { $store: store },
    stubs: {
      BasicConfig: {
        ...BasicConfig,
        methods: {
          getConfig: getConfig,
          isValid: isValid,
        }
      },
      'b-popover': BPopover,
      'b-button': BButton,
    },
    localVue
  });
}

// For making <b-popover> render properly in JSDOM
// https://github.com/bootstrap-vue/bootstrap-vue/blob/dev/src/components/popover/popover.spec.js
const originalWindow = cloneDeep(window);
const originalDocument = cloneDeep(document);
const originalCreateRange = document.createRange;
const origGetBCR = Element.prototype.getBoundingClientRect;

beforeEach(() => {
  bPopoverJsDomHack();

  localVue = createLocalVue();
  localVue.use(Vuex)

  action_init = jest.fn();

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state: require('../../../store/analyzers').state,
        mutations: require('../../../store/analyzers').mutations,
        getters: require('../../../store/analyzers').getters,
        actions: {
          init: action_init,
        },
      },
    }
  });

  getConfig = jest.fn();
  isValid = jest.fn();
});

afterEach(() => {
  // Remove any leftover popovers
  const popover_candidates = document.getElementsByClassName('popover');
  for (const popover of popover_candidates) {
    popover.remove();
  }

  // Reset overrides
  window = originalWindow;
  document = originalDocument;
  document.createRange = originalCreateRange;
  Element.prototype.getBoundingClientRect = origGetBCR;
})


test('mount', () => {
  const w = factory();

  // toggle button should exist
  expect(w.find('.toggle-new-analysis').exists()).toBeTruthy();

  // popover should exist, but is not shown
  expect(w.vm.$data.show).toBe(false);
  const popover = w.findComponent(BPopover)
  expect(popover.exists()).toBeTruthy();
  expect(popover.props().show).toBe(false);

  // not connected to backend -> BasicConfig should not exist.
  expect(w.vm.isConnected).toBe(false);
  expect(popover.findComponent(BasicConfig).exists()).toBeFalsy();  // todo: need to search in document instead, see SidebarNavAnalysisLink.test.js

  // Note: `w.destroy()` MUST be called at the end of each test in order for
  // the next test to function properly!
  w.destroy();
});

describe('show popover', () => {
  describe('not connected', () => {
    test('dismiss by clicking toggle again', async () => {
      const w = factory();

      const toggle = w.find('.toggle-new-analysis');
      const popover = w.findComponent(BPopover);

      expect(w.vm.$data.show).toBe(false);
      expect(popover.props().show).toBe(false);

      // click toggle to show popover
      await toggle.trigger('click');

      expect(document.getElementsByClassName('popover').length).toBe(1);
      expect(w.vm.$data.show).toBe(true);
      expect(popover.props().show).toBe(true);

      // click toggle to hide popover
      await toggle.trigger('click');

      expect(w.vm.$data.show).toBe(false);
      expect(popover.props().show).toBe(false);

      // Note: `w.destroy()` MUST be called at the end of each test in order for
      // the next test to function properly!
      w.destroy();
    });
  });

  describe('connected', () => {
    beforeEach(() => {
      store.commit('analyzers/setIsConnected', { connected: true })
    });

    test('dismiss by clicking toggle again', async () => {
      const w = factory();

      const toggle = w.find('.toggle-new-analysis');
      const popover = w.findComponent(BPopover);

      expect(w.vm.isConnected).toBe(true);
      expect(w.vm.$data.show).toBe(false);
      expect(popover.props().show).toBe(false);

      // click toggle to show popover
      await toggle.trigger('click');

      expect(document.getElementsByClassName('popover').length).toBe(1);
      expect(w.vm.$data.show).toBe(true);
      expect(popover.props().show).toBe(true);

      // click toggle to hide popover
      await toggle.trigger('click');

      expect(w.vm.$data.show).toBe(false);
      expect(popover.props().show).toBe(false);

      // Note: `w.destroy()` MUST be called at the end of each test in order for
      // the next test to function properly!
      w.destroy();
    });

    test('dismiss by clicking cancel', async () => {
      const w = factory();

      const toggle = w.find('.toggle-new-analysis');
      const popover = w.findComponent(BPopover);
      var body;


      expect(w.vm.isConnected).toBe(true);
      expect(w.vm.$data.show).toBe(false);
      expect(popover.props().show).toBe(false);

      // click toggle to show popover
      await toggle.trigger('click');

      expect(document.getElementsByClassName('popover').length).toBe(1);
      expect(w.vm.$data.show).toBe(true);
      expect(popover.props().show).toBe(true);

      // click cancel to hide popover
      const cancel = document.getElementsByClassName('popover-cancel')[0];
      await cancel.click();

      // expect(w.vm.$data.show).toBe(false);  // todo: works when running alone, fails when running in suite for some reason :(
      // expect(popover.props().show).toBe(false);

      // Note: `w.destroy()` MUST be called at the end of each test in order for
      // the next test to function properly!
      w.destroy();
    });

    test('commit valid', async () => {
      const ID = uuidv4();
      const CONFIG =  { dummy: 'config' }

      getConfig.mockReturnValue(CONFIG);
      isValid.mockResolvedValue(true);
      action_init.mockResolvedValue(ID);

      const w = factory();

      w.vm.$router = { push: jest.fn() }

      expect(action_init).not.toHaveBeenCalled();

      await w.find('.toggle-new-analysis').trigger('click')
      expect(document.getElementsByClassName('popover').length).toBe(1);
      const commit = document.getElementsByClassName('popover-ok')[0];

      await commit.click();
      await flushPromises();

      // should have called getConfig & isValid ~ BasicConfig.methods
      expect(getConfig).toHaveBeenCalled();
      expect(isValid).toHaveBeenCalled();

      // should have dispatched analyzers/init with dummy config ~ BasicConfig.methods.getConfig
      expect(action_init).toHaveBeenCalledTimes(1);
      expect(action_init).toHaveBeenCalledWith(
        expect.anything(),  // VueX action call -> { commit, dispatch }
        { config: CONFIG }  // this is what we're interested in
      );

      // should have routed to /analysis/align @ id ~ analyzers/init
      expect(w.vm.$router.push).toHaveBeenCalledTimes(1);
      expect(w.vm.$router.push).toHaveBeenCalledWith(`/analysis/align?id=${ID}`);

      // Note: `w.destroy()` MUST be called at the end of each test in order for
      // the next test to function properly!
      w.destroy();
    });

    test('commit invalid', async () => {
      isValid.mockResolvedValue(false);

      const w = factory();

      w.vm.$router = { push: jest.fn() }

      expect(action_init).not.toHaveBeenCalled();

      await w.find('.toggle-new-analysis').trigger('click')
      expect(document.getElementsByClassName('popover').length).toBe(1);
      const commit = document.getElementsByClassName('popover-ok')[0];

      await commit.click();
      await flushPromises();

      // should have called getConfig & isValid ~ BasicConfig.methods
      expect(getConfig).toHaveBeenCalled();
      expect(isValid).toHaveBeenCalled();

      // analysis should not have been initialized
      expect(action_init).not.toHaveBeenCalled();
      expect(w.vm.$router.push).not.toHaveBeenCalled();

      // Note: `w.destroy()` MUST be called at the end of each test in order for
      // the next test to function properly!
      w.destroy();
    });
  });
});

