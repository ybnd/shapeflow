import {createLocalVue, mount} from "@vue/test-utils";
import {beforeEach, describe, test} from "@jest/globals";

import {getters, mutations, actions, state} from '../../../store/analyzers'
import Sidebar from "../Sidebar";
import SidebarHeader from "../SidebarHeader";
import SidebarNavLink from "../SidebarNavLink";
import draggable from "vuedraggable";
import SidebarNavAnalysis from "../SidebarNavAnalysis";
import SidebarNavAnalysisLink from "../SidebarNavAnalysisLink";
import SidebarNewAnalysis from "../SidebarNewAnalysis";
import BasicConfig from "../../config/BasicConfig";
import SidebarFooter from "../SidebarFooter";
import { BPopover, BProgress } from "bootstrap-vue";
import Waiting from "../Waiting";
import {uuidv4} from "../../../static/util";
import Vuex from "vuex";
import VueRouter from "vue-router";
import {AnalyzerState} from "../../../static/api";
import {events} from "../../../static/events";
import flushPromises from "flush-promises";
import { shuffle } from 'lodash'


var localVue;
var store;

var action_loop;
var action_stop;


beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex)

  action_loop = jest.fn();
  action_stop = jest.fn();

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        actions: {
          loop: action_loop,
          stop: action_stop,
        },
        state,
        mutations,
        getters
      },
    },
  });
});

function factory () {
  localVue.use(VueRouter)
  const router = new VueRouter();

  return mount(Sidebar, {
    mocks: { $store: store},
    stubs: {
      SidebarHeader,
      SidebarNavLink,
      SidebarNavAnalysis,
      SidebarNavAnalysisLink,
      SidebarNewAnalysis,
      BasicConfig,
      SidebarFooter,
      draggable,
      'b-popover': BPopover,
      'b-progress': BProgress,
    },
    localVue,
    router
  })
}

function addAnalysis (id, name = '#1', state = AnalyzerState.LAUNCHED) {
  if ( id === undefined) {
    id = uuidv4();
  }

  store.commit('analyzers/addAnalyzer', { id: id });
  store.commit('analyzers/setAnalyzerConfig', { id: id, config: { name: name }})
  store.commit('analyzers/setAnalyzerStatus', { id: id, status: { state: state }})
  store.commit('analyzers/addToQueue', { id: id })
}

function dropAnalysis (id) {
  store.commit('analyzers/dropFromQueue', { id: id })
  store.commit('analyzers/dropAnalyzer', { id: id })
}

test('mount', () => {
  const w = factory();

  expect(w.findComponent(Sidebar).exists()).toBeTruthy();
  expect(w.findComponent(SidebarHeader).exists()).toBeTruthy();
  expect(w.findComponent(draggable).exists()).toBeTruthy();
  expect(w.findComponent(SidebarNewAnalysis).exists()).toBeTruthy();
  expect(w.findComponent(SidebarFooter).exists()).toBeTruthy();

  // queue is empty, so no analyses present
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.length).toBe(0);
});

test('destroy', () => {
  const w = factory();

  expect(action_loop).toHaveBeenCalled();
  expect(action_stop).not.toHaveBeenCalled();

  w.destroy()

  expect(action_stop).toHaveBeenCalled();
});

test('add & remove analyzers', async () => {
  const ID1 = uuidv4();
  const ID2 = uuidv4();

  // Initialize store;
  addAnalysis();
  addAnalysis(ID1);

  const w = factory();

  // 2 analyses in queue
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.length).toBe(2);

  // Add some more
  addAnalysis();
  await w.vm.$nextTick();
  addAnalysis(ID2);
  await w.vm.$nextTick();
  addAnalysis();
  await w.vm.$nextTick();

  // 5 analyses in queue
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.length).toBe(5);

  // Drop some
  dropAnalysis(ID1);  // todo: weird bug with analyzers/dropFromQueue...
  await w.vm.$nextTick();
  dropAnalysis(ID2);
  await w.vm.$nextTick();

  // 3 analyses in queue
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.length).toBe(3);
});

test('queue order', async () => {
  // Initialize store
  const QUEUE = [uuidv4(), uuidv4(), uuidv4(), uuidv4()];
  for (const ID of QUEUE) {
    addAnalysis(ID);
  }

  const w = factory();

  // Analyses are ordered by queue
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.map(w => w.vm.id)).toStrictEqual(QUEUE);
});

test('queue reordering', async () => {
  // Initialize store
  const QUEUE = [uuidv4(), uuidv4(), uuidv4(), uuidv4()];
  for (const ID of QUEUE) {
    addAnalysis(ID);
  }

  const w = factory();

  // Analyses are ordered by queue
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.map(w => w.vm.id)).toStrictEqual(QUEUE);

  // Reorder queue ~ store commit
  const REORDERED_1 = shuffle(QUEUE);
  store.commit('analyzers/setQueue', { queue: REORDERED_1 });
  await w.vm.$nextTick();
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.map(w => w.vm.id)).toStrictEqual(REORDERED_1);

  // Reorder queue ~ assignment to Sidebar.queue
  const REORDERED = shuffle(QUEUE);
  w.vm.queue = REORDERED
  await w.vm.$nextTick();
  expect(w.findAllComponents(SidebarNavAnalysis).wrappers.map(w => w.vm.id)).toStrictEqual(REORDERED);
});

test('highlight & open on route change to analyzer page', async () => {
  // Initialize store;
  const ID = uuidv4();
  addAnalysis(ID);

  const w = factory();
  const from = w.vm.$route.fullPath;

  w.vm.$root.$emit = jest.fn();

  // Change $route
  const to = '/something?id=' + ID;
  await w.vm.$router.push(to)

  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.unhighlight(from));
  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.highlight(to));
  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.open(ID));
});

test('highlight & open on route change to settings page', async () => {
  const w = factory();
  const from = w.vm.$route.fullPath;

  w.vm.$root.$emit = jest.fn();

  // Change $route
  const to = '/settings';
  await w.vm.$router.push(to)

  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.unhighlight(from));
  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.highlight(to));
  expect(w.vm.$root.$emit).toHaveBeenCalledWith(events.sidebar.open('Application'));
});
