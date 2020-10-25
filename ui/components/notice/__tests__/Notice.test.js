import {createLocalVue, shallowMount} from "@vue/test-utils";
import Vuex from "vuex";
import {beforeEach, describe, test} from "@jest/globals";

import Notice from "../Notice";
import {BAlert} from "bootstrap-vue";


var NOTICE;
var store;

beforeEach(() => {
  const localVue = createLocalVue();
  localVue.use(Vuex)

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        state: require('../../../store/analyzers').state,
        mutations: require('../../../store/analyzers').mutations,
        getters: require('../../../store/analyzers').getters,
      },
    }
  })

  store.commit('analyzers/newNotice', {id: undefined, notice: {message: 'a message'}});
  NOTICE = store.getters['analyzers/getNotices'][0];
})

function factory (notice) {
  return shallowMount(
    Notice, {
      propsData: {
        notice: notice,
      },
      mocks: {
        $store: store,
      },
      stubs: {
        'b-alert': BAlert,
      }
    }
  )
}


test('mount', () => {
  const w = factory(NOTICE);
  expect(w.find('p').text()).toBe(NOTICE.message);
  expect(w.vm.$data.timeout).not.toBe(null);
});

test('dismiss', async () => {
  const w = factory(NOTICE);
  await w.find('button').trigger('click');

  expect(store.getters['analyzers/getNotices']).toStrictEqual([]);
});

test('destroy', () => {
  const w = factory(NOTICE);
  w.destroy();
});



