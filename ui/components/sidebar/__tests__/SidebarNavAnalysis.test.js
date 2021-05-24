import {createLocalVue, mount} from "@vue/test-utils";
import {beforeEach, describe, test} from "@jest/globals";

import {getters, mutations, state} from '../../../store/analyzers'
import SidebarNavAnalysis from "../SidebarNavAnalysis";
import SidebarNavAnalysisLink from "../SidebarNavAnalysisLink";
import Waiting from "../Waiting";
import {uuidv4} from "../../../src/util";
import Vuex from "vuex";
import {BProgress} from "bootstrap-vue";
import {AnalyzerState} from "../../../src/api";
import {events} from "../../../src/events";
import axios from 'axios';
import flushPromises from "flush-promises";

jest.mock('axios');


const ID = uuidv4();
const NAME = '#1';
const STATUS = { progress: 0.0, state: AnalyzerState.UNKNOWN }
const ROUTE = { path: '/something', query: { id: ID } };

var localVue;
var store;
var action_close;
var action_sync;


beforeEach(() => {
  localVue = createLocalVue();
  localVue.use(Vuex)

  action_close = jest.fn();
  action_sync = jest.fn();

  store = new Vuex.Store({
    modules: {
      analyzers: {
        namespaced: true,
        actions: {
          close: action_close,
          sync: action_sync,
        },
        state,
        mutations,
        getters
      },
    },
  })
});


function factory () {
  return mount(SidebarNavAnalysis, {
    propsData: { id: ID },
    mocks: { $store: store, $route: ROUTE },
    stubs: {
      SidebarNavAnalysisLink: SidebarNavAnalysisLink,
      Waiting: Waiting,
      'b-progress': BProgress,
    },
    localVue,
  })
}


test('mount', () => {
  store.commit('analyzers/addAnalyzer', {id: ID});
  store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})
  store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

  const w = factory();

  expect(w.find('.analysis-name').exists()).toBeFalsy();  // waiting until AnalyzerState.LAUNCHED
  expect(w.findComponent(Waiting).exists()).toBeTruthy();
});

test('undefined name', () => {
  store.commit('analyzers/addAnalyzer', {id: ID});
  store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

  const w = factory();

  // No config to get name from -> .analysis-name should be replaced by <Waiting/>
  expect(w.vm.name).toBe(undefined);
  expect(w.find('.analysis-name').exists()).toBeFalsy();
  expect(w.findComponent(Waiting).exists()).toBeTruthy();
});

test('toggle', async () => {
  store.commit('analyzers/addAnalyzer', {id: ID});
  store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})
  store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

  const w = factory();
  const toggle = w.find('.nav-dropdown-toggle');
  const dropdown = w.find('.nav-dropdown');

  // closed by default
  expect(dropdown.element.className).not.toContain('open');

  // click -> open
  await toggle.trigger('click');
  expect(dropdown.element.className).toContain('open');

  // click -> closed
  await toggle.trigger('click');
  expect(dropdown.element.className).not.toContain('open');
});

describe('events', () => {
  test('open', async () => {
    store.commit('analyzers/addAnalyzer', {id: ID});
    store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

    const w = factory();
    const dropdown = w.find('.nav-dropdown');

    // closed by default
    expect(dropdown.element.className).not.toContain('open');

    // emit event -> open
    await w.vm.$root.$emit(events.sidebar.open(ID))
    expect(dropdown.element.className).toContain('open');

    // event doesn't toggle, can only open
    await w.vm.$root.$emit(events.sidebar.open(ID))
    expect(dropdown.element.className).toContain('open');
  });

  test('remove', async () => {
    store.commit('analyzers/addAnalyzer', {id: ID});
    store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

    const w = factory();

    var route_to = '';
    w.vm.$router = {
      push: jest.fn((to) => {
        route_to = to;
      })
    };
    expect(action_close).toHaveBeenCalledTimes(0);
    expect(w.vm.$router.push).toHaveBeenCalledTimes(0);

    // emit event -> should call action_close & push router to '/'
    await w.vm.$root.$emit(events.sidebar.close(ID));
    expect(action_close).toHaveBeenCalledTimes(1);
    expect(w.vm.$router.push).toHaveBeenCalledTimes(1);
    expect(route_to).toBe('/');
  });

  test('cancel', async () => {
    store.commit('analyzers/addAnalyzer', {id: ID});
    store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: STATUS});

    const w = factory();

    expect(action_sync).toHaveBeenCalledTimes(0);

    // emit event -> should call cancel() & action_sync
    axios.post.mockResolvedValueOnce({
      status: 200, data: true,
    })
    await w.vm.$root.$emit(events.sidebar.cancel(ID));
    // expect(action_sync).toHaveBeenCalledTimes(1);  // todo: doesn't increase for some reason...
  });
});

describe('status.state', () => {
  var w;
  var items;
  var link;

  beforeEach(() => {
    store.commit('analyzers/addAnalyzer', {id: ID});
    store.commit('analyzers/setAnalyzerConfig', {id: ID, config: {name: NAME}})

    w = factory();

  });

  function gather () {
    items = w.findAllComponents(SidebarNavAnalysisLink).wrappers.reduce(
      (o, item) => {
        return {
          ...o, [item.vm.id]: item.find('.sidebar-analysis-link')
        }
      }, {}
    );
    link = w.vm.link;
  }

  test('undefined', async () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: undefined}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).toContain('disabled');
    expect(items[link.align].classes()).toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('UNKNOWN', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.UNKNOWN}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('INCOMPLETE', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.INCOMPLETE}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('CAN_LAUNCH', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.CAN_LAUNCH}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('LAUNCHED', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.LAUNCHED}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('CAN_FILTER', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.CAN_FILTER}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).not.toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('CAN_ANALYZE', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.CAN_ANALYZE}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).not.toContain('disabled');
    expect(items[link.result].classes()).not.toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).not.toContain('disabled');
  });

  test('ANALYZING', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.ANALYZING}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).toContain('disabled');
    expect(items[link.align].classes()).toContain('disabled');
    expect(items[link.filter].classes()).toContain('disabled');
    expect(items[link.result].classes()).toContain('disabled');

    expect(items).not.toHaveProperty(link.analyze);
    expect(items).toHaveProperty(link.cancel);

    expect(items[link.cancel].classes()).not.toContain('disabled');
  });

  test('DONE', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.DONE}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).not.toContain('disabled');
    expect(items[link.result].classes()).not.toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).toContain('disabled');
  });

  test('CANCELED', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.CANCELED}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).not.toContain('disabled');
    expect(items[link.result].classes()).not.toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).not.toContain('disabled');
  });

  test('ERROR', () => {
    store.commit('analyzers/setAnalyzerStatus', {id: ID, status: {state: AnalyzerState.ERROR}});
    w = factory();
    gather();

    expect(items[link.configure].classes()).not.toContain('disabled');
    expect(items[link.align].classes()).not.toContain('disabled');
    expect(items[link.filter].classes()).not.toContain('disabled');
    expect(items[link.result].classes()).not.toContain('disabled');

    expect(items).toHaveProperty(link.analyze);
    expect(items).not.toHaveProperty(link.cancel);

    expect(items[link.analyze].classes()).not.toContain('disabled');
  });

});
