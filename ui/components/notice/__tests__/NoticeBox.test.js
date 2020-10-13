import {createLocalVue, mount} from "@vue/test-utils";
import Vuex from "vuex";
import {beforeEach, test} from "@jest/globals";

import NoticeBox from "../NoticeBox";
import Notice from "../Notice";
import {BAlert} from "bootstrap-vue";
import flushPromises from "flush-promises";


var store;  // VueX store
const MESSAGES = [
  'first notice',
  'second notice',
  'third notice',
  'fouyrth notice'
]


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
  });
})

function factory () {
  return mount(
    NoticeBox, {
      mocks: {
        $store: store,
      },
      stubs: {
        'b-alert': BAlert,
        'Notice': Notice
      },
    },
  )
}

test('mount', () => {
  const w = factory();

  // No notices in the store yet
  expect(w.vm.notices).toStrictEqual([]);

  // No elements under <NoticeBox>
  expect(w.vm.$children.length).toBe(0);
});

test('follow analyzers/newNotice', async () => {
  const w = factory();

  for (let i = 0; i < MESSAGES.length; i++) {
    expect(w.vm.$children.length).toBe(i);
    store.commit('analyzers/newNotice', {id: undefined, notice: {message: MESSAGES[i]}});
    await flushPromises();
    await w.vm.$nextTick();
    expect(w.vm.$children.length).toBe(i+1);
  }

  expect(
    w.findAllComponents(Notice).wrappers.map(
      w => w.find('p').text()
    )
  ).toStrictEqual(MESSAGES);
});

test('follow analyzers/dismissNotice', async () => {
  const w = factory();

  for (let i = 0; i < MESSAGES.length; i++) {
    store.commit('analyzers/newNotice', {id: undefined, notice: {message: MESSAGES[i]}});
  }

  await flushPromises();
  await w.vm.$nextTick();

  for (let i = 3; i >= 0; i--) {
    expect(w.vm.$children.length).toBe(i+1);
    store.commit('analyzers/dismissNotice', {notice: store.getters['analyzers/getNotices'][i]});
    await flushPromises();
    await w.vm.$nextTick();
    expect(w.vm.$children.length).toBe(i);
  }
});
