import {getters, mutations, actions, state, LOAD_INTERVAL, MAX_TIME_WITHOUT_CONTACT, SYNC_INTERVAL} from '../analyzers'
import {NOTICE_LIMIT, QueueState, api} from "../../static/api";
import {uuidv4} from "../../static/util";
import axios from 'axios';
import {beforeEach, describe, test} from "@jest/globals";
import {waitSync} from "../../static/shapeflow";
import {createLocalVue} from "@vue/test-utils";
import Vuex from "vuex";
import EventSource from 'eventsourcemock';
import {sources} from 'eventsourcemock';

jest.mock('axios');

test('state', () => {
  const STATE = state();
  expect(STATE.last_heard_from_backend).toBe(null);
  expect(STATE.is_connected).toBe(false);
  expect(STATE.queue.length).toBe(0);
  expect(STATE.queue_state).toBe(QueueState.STOPPED);
  expect(STATE.source).toBe(null)
})

describe('mutations & getters', () => {
  test('backendIsUp', () => {
    const STATE = state();
    expect(getters.getLastBackendContact(STATE)).toBe(null);

    mutations.backendIsUp(STATE);
    expect(getters.getLastBackendContact(STATE)).not.toBe(null);
    const first =getters.getLastBackendContact(STATE);

    waitSync(100);
    mutations.backendIsUp(STATE);
    expect(getters.getLastBackendContact(STATE)).not.toBe(null);
    expect(getters.getLastBackendContact(STATE)).not.toBe(first);
  });

  test('setIsConnected', () => {
    const STATE = state();
    expect(getters.isConnected(STATE)).toBe(false);

    mutations.setIsConnected(STATE, {connected: true});
    expect(getters.isConnected(STATE)).toBe(true);
  });

  test('setSource -> valid', () => {
    const STATE = state();
    expect(STATE.source).toBe(null);
    expect(getters.hasSource(STATE)).toBe(false);

    const SOURCE = { dummy: 'object' };
    mutations.setSource(STATE, {source: SOURCE});
    expect(STATE.source).toStrictEqual(SOURCE);
    expect(getters.hasSource(STATE)).toBe(true);
  });

  test('setSource -> undefined', () => {
    const STATE = state();
    expect(STATE.source).toBe(null);
    expect(getters.hasSource(STATE)).toBe(false);

    mutations.setSource(STATE, {source: undefined});
    expect(STATE.source).toBe(null);
    expect(getters.hasSource(STATE)).toBe(false);

    const SOURCE = { dummy: 'object' };
    mutations.setSource(STATE, {source: SOURCE});
    expect(STATE.source).toStrictEqual(SOURCE);

    mutations.setSource(STATE, {source: undefined});
    expect(STATE.source).toStrictEqual(SOURCE);
    expect(getters.hasSource(STATE)).toBe(true);
  });

  test('closeSource', () => {
    const STATE = state();
    expect(STATE.source).toBe(null);
    expect(getters.hasSource(STATE)).toBe(false);

    var close_calls = 0;
    const SOURCE = {dummy: 'object', close: () => {close_calls++}};
    mutations.setSource(STATE, {source: SOURCE});
    expect(STATE.source).toStrictEqual(SOURCE);
    expect(getters.hasSource(STATE)).toBe(true);
    expect(close_calls).toBe(0)

    mutations.closeSource(STATE);
    expect(STATE.source).toBe(null);
    expect(getters.hasSource(STATE)).toBe(false);
    expect(close_calls).toBe(1)
  });

  test('setQueueState -> valid', () => {
    const STATE = state();
    expect(getters.getQueueState(STATE)).toBe(QueueState.STOPPED);

    mutations.setQueueState(STATE, {queue_state: QueueState.RUNNING});
    expect(getters.getQueueState(STATE)).toBe(QueueState.RUNNING);

    mutations.setQueueState(STATE, {queue_state: QueueState.STOPPED});
    expect(getters.getQueueState(STATE)).toBe(QueueState.STOPPED);
  });

  test('setQueueState -> undefined', () => {
    const STATE = state();
    expect(getters.getQueueState(STATE)).toBe(QueueState.STOPPED);

    mutations.setQueueState(STATE, {queue_state: undefined});
    expect(getters.getQueueState(STATE)).toBe(QueueState.STOPPED);

    mutations.setQueueState(STATE, {queue_state: QueueState.RUNNING});
    expect(getters.getQueueState(STATE)).toBe(QueueState.RUNNING);

    mutations.setQueueState(STATE, {queue_state: undefined});
    expect(getters.getQueueState(STATE)).toBe(QueueState.RUNNING);
  });

  test('addAnalyzer -> valid', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    const ID2 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID2});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});
  });

  test('addAnalyzer -> duplicate id', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});  // todo: will probably erase config & status
    expect(STATE.status).toStrictEqual({[ID1]: {}});
  });

  test('addAnalyzer -> undefined id', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    mutations.addAnalyzer(STATE, {id: undefined});
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    mutations.addAnalyzer(STATE, {id: undefined});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    const ID2 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID2});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});

    mutations.addAnalyzer(STATE, {id: undefined});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});
  });

  test('setAnalyzerStatus -> valid', () => {
    const STATE = state();
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    const STATUS1 = {dummy: 'object1'};
    mutations.addAnalyzer(STATE, {id: ID1});
    mutations.setAnalyzerStatus(STATE, {id: ID1, status: STATUS1});
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS1);

    const ID2 = uuidv4();
    const STATUS2 = {dummy: 'object2'};
    mutations.addAnalyzer(STATE, {id: ID2});
    mutations.setAnalyzerStatus(STATE, {id: ID2, status: STATUS2});
    expect(getters.getAnalyzerStatus(STATE)(ID2)).toStrictEqual(STATUS2);
    expect(getters.getFullStatus(STATE)).toStrictEqual({[ID1]: STATUS1, [ID2]: STATUS2});

    mutations.setAnalyzerStatus(STATE, {id: ID1, status: STATUS2});
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS2);
    expect(getters.getFullStatus(STATE)).toStrictEqual({[ID1]: STATUS2, [ID2]: STATUS2});
  });

  test('setAnalyzerStatus -> undefined id', () => {
    const STATE = state();
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    const STATUS1 = {dummy: 'object'};
    mutations.addAnalyzer(STATE, {id: ID1});

    mutations.setAnalyzerStatus(STATE, {id: ID1, status: STATUS1});
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS1);

    mutations.setAnalyzerStatus(STATE, {id: undefined, status: STATUS1});
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS1);
  });

  test('setAnalyzerStatus -> undefined status', () => {
    const STATE = state();
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    const STATUS1 = {dummy: 'object'};
    mutations.addAnalyzer(STATE, {id: ID1});

    mutations.setAnalyzerStatus(STATE, {id: ID1, status: STATUS1});
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS1);

    mutations.setAnalyzerStatus(STATE, {id: ID1, status: undefined})
    expect(getters.getAnalyzerStatus(STATE)(ID1)).toStrictEqual(STATUS1);
  });

  test('setAnalyzerConfig -> valid', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});

    const ID1 = uuidv4();
    const CONFIG1 = {dummy: 'object1', name: 'a name'};
    mutations.addAnalyzer(STATE, {id: ID1});
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG1})
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG1);

    const CONFIG2 = {dummy: 'object2', name: 'another name'};
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG2});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG2);
  });

  test('setAnalyzerConfig -> valid, no name', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});

    const ID1 = uuidv4();
    const CONFIG1 = {dummy: 'object1'};
    mutations.addAnalyzer(STATE, {id: ID1});
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG1});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual({...CONFIG1, name: '!! unnamed !!'});

    const CONFIG2 = {dummy: 'object2'};
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG2});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual({...CONFIG2, name: '!! unnamed !!'});
  });

  test('setAnalyzerConfig -> undefined id', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});

    const ID1 = uuidv4();
    const CONFIG1 = {dummy: 'object1', name: '1'};

    mutations.addAnalyzer(STATE, {id: ID1});
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG1});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG1);

    const CONFIG2 = {dummy: 'object2', name: '2'};
    mutations.setAnalyzerConfig(STATE, {id: undefined, config: CONFIG2});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG1);
  });

  test('setAnalyzerConfig -> undefined config', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});

    const ID1 = uuidv4();
    const CONFIG1 = {dummy: 'object1', name: '1'};

    mutations.addAnalyzer(STATE, {id: ID1});
    mutations.setAnalyzerConfig(STATE, {id: ID1, config: CONFIG1});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG1);

    mutations.setAnalyzerConfig(STATE, {id: ID1, config: undefined});
    expect(getters.getAnalyzerConfig(STATE)(ID1)).toStrictEqual(CONFIG1);
  });

  test('dropAnalyzer -> valid', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    const ID2 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID2});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});

    mutations.dropAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID2]: {}});

    mutations.dropAnalyzer(STATE, {id: ID2})
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});
  });

  test('dropAnalyzer -> undefined id', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    const ID2 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID2});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});

    mutations.dropAnalyzer(STATE, {id: undefined});
    expect(STATE.config).toStrictEqual({[ID1]: {}, [ID2]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}, [ID2]: {}});
  });

  test('dropAnalyzer -> unknown id', () => {
    const STATE = state();
    expect(STATE.config).toStrictEqual({});
    expect(STATE.status).toStrictEqual({});

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});

    const ID2 = uuidv4();

    mutations.dropAnalyzer(STATE, {id: ID2});
    expect(STATE.config).toStrictEqual({[ID1]: {}});
    expect(STATE.status).toStrictEqual({[ID1]: {}});
  });

  test('addToQueue -> valid', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addToQueue(STATE, {id: ID1});
    expect(STATE.queue).toStrictEqual([ID1]);

    const ID2 = uuidv4();
    mutations.addToQueue(STATE, {id: ID2});
    expect(STATE.queue).toStrictEqual([ID1, ID2]);
  });

  test('addToQueue -> undefined id', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    mutations.addToQueue(STATE, {id: undefined});
    expect(STATE.queue).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addToQueue(STATE, {id: ID1});
    expect(STATE.queue).toStrictEqual([ID1]);

    mutations.addToQueue(STATE, {id: undefined});
    expect(STATE.queue).toStrictEqual([ID1]);
  });

  test('dropFromQueue -> valid', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addToQueue(STATE, {id: ID1});
    expect(STATE.queue).toStrictEqual([ID1]);

    const ID2 = uuidv4();
    mutations.addToQueue(STATE, {id: ID2});
    expect(STATE.queue).toStrictEqual([ID1, ID2]);

    mutations.dropFromQueue(STATE, {id: ID2})
    expect(STATE.queue).toStrictEqual([ID1]);

    mutations.dropFromQueue(STATE, {id: ID1})
    expect(STATE.queue).toStrictEqual([]);
  });

  test('dropFromQueue -> unknown id', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addToQueue(STATE, {id: ID1});
    expect(STATE.queue).toStrictEqual([ID1]);

    const ID2 = uuidv4();
    mutations.addToQueue(STATE, {id: ID2});
    expect(STATE.queue).toStrictEqual([ID1, ID2]);

    mutations.dropFromQueue(STATE, {id: uuidv4()})
    expect(STATE.queue).toStrictEqual([ID1, ID2]);
  });

  test('dropFromQueue -> undefined id', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addToQueue(STATE, {id: ID1});
    expect(STATE.queue).toStrictEqual([ID1]);

    const ID2 = uuidv4();
    mutations.addToQueue(STATE, {id: ID2});
    expect(STATE.queue).toStrictEqual([ID1, ID2]);

    mutations.dropFromQueue(STATE, {id: undefined})
    expect(STATE.queue).toStrictEqual([ID1, ID2]);
  });

  test('setQueue -> valid', () => {
    const STATE = state();
    expect(STATE.queue).toStrictEqual([]);

    const QUEUE = [uuidv4(), uuidv4()];
    mutations.setQueue(STATE, {queue: QUEUE});
    expect(STATE.queue).toStrictEqual(QUEUE);
  });

  test('getQueue', () => {
    const STATE = state();
    expect(getters.getQueue(STATE)).toStrictEqual([]);

    const QUEUE = [uuidv4(), uuidv4()];
    mutations.setQueue(STATE, {queue: QUEUE});
    expect(getters.getQueue(STATE)).toStrictEqual(QUEUE);
  });

  test('getIndex', () => {
    const STATE = state();
    expect(getters.getQueue(STATE)).toStrictEqual([]);

    const QUEUE = [uuidv4(), uuidv4()];
    mutations.setQueue(STATE, {queue: QUEUE});
    expect(getters.getIndex(STATE)(QUEUE[0])).toBe(0);
    expect(getters.getIndex(STATE)(QUEUE[1])).toBe(1);
  });

  test('isValidId', () => {
    const STATE = state();
    expect(getters.getQueue(STATE)).toStrictEqual([]);

    const QUEUE = [uuidv4(), uuidv4()];
    expect(getters.isValidId(STATE)(QUEUE[0])).toBe(undefined);
    expect(getters.isValidId(STATE)(QUEUE[1])).toBe(undefined);
    mutations.setQueue(STATE, {queue: QUEUE});
    expect(getters.isValidId(STATE)(QUEUE[0])).toBe(undefined);
    expect(getters.isValidId(STATE)(QUEUE[1])).toBe(undefined);

    waitSync(LOAD_INTERVAL + 100);
    expect(getters.isValidId(STATE)(QUEUE[0])).toBe(true);
    expect(getters.isValidId(STATE)(QUEUE[1])).toBe(true);
    expect(getters.isValidId(STATE)(uuidv4())).toBe(false);
  });

  test('newNotice -> valid', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something'};
    const NOTICE2 = {message: 'something else'};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices[0]).toMatchObject(NOTICE1)

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(STATE.notices[1]).toMatchObject(NOTICE2)
  });

  test('newNotice -> valid, with uuid', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something', uuid: uuidv4()};
    const NOTICE2 = {message: 'something else', uuid: uuidv4()};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices[0]).toMatchObject(NOTICE1);

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(STATE.notices[1]).toMatchObject(NOTICE2);
  });

  test('newNotice -> valid, with uuid, double push', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something', uuid: uuidv4()};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);
  });

  test('newNotice -> undefined id', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const NOTICE1 = {message: 'something'};
    const NOTICE2 = {message: 'something else'};

    mutations.newNotice(STATE, {notice: NOTICE1});
    expect(STATE.notices[0]).toMatchObject(NOTICE1)

    mutations.newNotice(STATE, {notice: NOTICE2});
    expect(STATE.notices[1]).toMatchObject(NOTICE2)
  });

  test('newNotice -> undefined notice', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const NOTICE1 = {message: 'something'};

    mutations.newNotice(STATE, {notice: undefined});
    expect(STATE.notices).toStrictEqual([])

    mutations.newNotice(STATE, {notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);
    expect(STATE.notices[0]).toMatchObject(NOTICE1);

    mutations.newNotice(STATE, {notice: undefined});
    expect(STATE.notices.length).toBe(1);
    expect(STATE.notices[0]).toMatchObject(NOTICE1);
  });

  test('newNotice -> enforce limit', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    var NOTICES = [];
    for (let i=0; i < NOTICE_LIMIT + 5; i++) {
      NOTICES = [...NOTICES, {message: `notice ${i}`}]
    }

    for (const NOTICE of NOTICES) {
      mutations.newNotice(STATE, {notice: NOTICE});
      expect(STATE.notices.length).toBeLessThanOrEqual(NOTICE_LIMIT);

      // current notice should be the last one in the array
      expect(STATE.notices[STATE.notices.length - 1]).toMatchObject(NOTICE);
    }
  });

  test('dismissNotice -> valid', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something'};
    const NOTICE2 = {message: 'something else'};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(STATE.notices.length).toBe(2);

    mutations.dismissNotice(STATE, {notice: STATE.notices[1]});
    expect(STATE.notices.length).toBe(1);

    mutations.dismissNotice(STATE, {notice: STATE.notices[0]});
    expect(STATE.notices.length).toBe(0);
  });

  test('dismissNotice -> not using actual values', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something'};
    const NOTICE2 = {message: 'something else'};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(STATE.notices.length).toBe(2);

    mutations.dismissNotice(STATE, {notice: NOTICE1});
    expect(STATE.notices.length).toBe(2);

    mutations.dismissNotice(STATE, {notice: NOTICE2});
    expect(STATE.notices.length).toBe(2);
  });

  test('dismissNotice -> undefined notice', () => {
    const STATE = state();
    expect(STATE.notices).toStrictEqual([]);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something'};
    const NOTICE2 = {message: 'something else'};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    expect(STATE.notices.length).toBe(1);

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(STATE.notices.length).toBe(2);

    mutations.dismissNotice(STATE, {notice: undefined});
    expect(STATE.notices.length).toBe(2);

    mutations.dismissNotice(STATE, {notice: undefined});
    expect(STATE.notices.length).toBe(2);
  });

  test('getNotices', () => {
    const STATE = state();
    expect(getters.getNotices(STATE)).toStrictEqual(STATE.notices);

    const ID1 = uuidv4();
    mutations.addAnalyzer(STATE, {id: ID1});

    const NOTICE1 = {message: 'something', uuid: uuidv4()};
    const NOTICE2 = {message: 'something else', uuid: uuidv4()};

    mutations.newNotice(STATE, {id: ID1, notice: NOTICE1});
    mutations.newNotice(STATE, {id: ID1, notice: NOTICE2});
    expect(getters.getNotices(STATE)).toStrictEqual(STATE.notices);
  });

  test('getAnalyzerConfigCopy -> no changes', () => {
    const STATE = state();
    const ID = uuidv4();
    const CONFIG = {
      name: '#1',
      features: ['something', 'something else'],
      masks: [
        {name: 'mask 1'}, {name: 'mask2'}, {name: 'mask3'},
      ],
      transform: {roi: {BL: {}, TL: {}, TR: {}, BR: {}}},
    };

    mutations.addAnalyzer(STATE, {id: ID});
    mutations.setAnalyzerConfig(STATE, {id: ID, config: CONFIG});

    var CONFIG_COPY = getters.getAnalyzerConfigCopy(STATE)(ID);
    expect(STATE.config[ID]).toStrictEqual(CONFIG_COPY);

    var CONFIG_REFERENCE = getters.getAnalyzerConfig(STATE)(ID);
    CONFIG_REFERENCE.name = '#2';

    expect(STATE.config[ID]).not.toStrictEqual(CONFIG_COPY);
    expect(CONFIG_COPY.name).toBe('#1');
  });

  test('get config parts', () => {
    const STATE = state();
    const ID = uuidv4();
    const CONFIG = {
      name: '#1',
      features: ['something', 'something else'],
      masks: [
        {name: 'mask 1'}, {name: 'mask2'}, {name: 'mask3'},
      ],
      transform: {roi: {BL: {}, TL: {}, TR: {}, BR: {}}},
    };

    mutations.addAnalyzer(STATE, {id: ID});
    mutations.setAnalyzerConfig(STATE, {id: ID, config: CONFIG})

    expect(getters.getName(STATE)(ID)).toBe(CONFIG.name);
    expect(getters.getFeatures(STATE)(ID)).toStrictEqual(CONFIG.features);
    expect(getters.getMasks(STATE)(ID)).toStrictEqual(CONFIG.masks);
    expect(getters.getRoi(STATE)(ID)).toStrictEqual(CONFIG.transform.roi);
  });
});

describe('actions', () => {
  var localVue = undefined;
  var store = undefined;
  window.EventSource = EventSource;

  beforeEach(() => {
    localVue = createLocalVue();
    localVue.use(Vuex)
    store = new Vuex.Store({
      state: state,
      mutations: mutations,
      getters: getters,
      actions: actions,
    });
  });

  afterEach(() => {
    store = undefined;
  });

  test('connection -> backend is up', () => {
    store.commit('setIsConnected', {connected: false});
    expect(store.getters['isConnected']).toBe(false);
    store.dispatch('connection', {ok: true});
    expect(store.getters['isConnected']).toBe(true);
  });

  test('connection -> backend was up just now', () => {
    store.commit('setIsConnected', {connected: false});
    store.commit('backendIsUp');
    waitSync(MAX_TIME_WITHOUT_CONTACT / 10);
    expect(store.getters['isConnected']).toBe(false);
    store.dispatch('connection', {ok: false});
    expect(store.getters['isConnected']).toBe(true);
  });

  test('connection -> backend is down', () => {
    store.commit('setIsConnected', {connected: false});
    expect(store.getters['isConnected']).toBe(false);
    store.dispatch('connection', {ok: false});
    expect(store.getters['isConnected']).toBe(false);
  });

  test('source -> backend is up', done => {
    axios.post.mockResolvedValue({status: 200});
    store.dispatch('source').then(() => {
      expect(store.getters['isConnected']).toBe(true);
      done();
    });
  });

  test('source -> backend is down', done => {
    axios.post.mockResolvedValue({status: 404});
    store.dispatch('source').then(() => {
      expect(store.getters['isConnected']).toBe(false);
      done();
    });
  });

  test('source -> handle message', done => {
    axios.post.mockResolvedValue({status: 200});
    store.dispatch('source').then(() => {
      expect(store.getters['isConnected']).toBe(true);
      expect(store.getters['getNotices'].length).toBe(0);

      store.state.source.emit('message', {
        data: JSON.stringify({
          category: 'notice',
          id: null,
          data: {message: 'notice me senpai'}
        })
      });

      expect(store.getters['getNotices'].length).toBe(1);
      expect(store.getters['getNotices'][0].message).toBe('notice me senpai');
      done();
    });
  });

  test('source -> error during message handling', done => {
    axios.post.mockResolvedValue({status: 200});
    store.dispatch('source').then(() => {
      expect(store.getters['isConnected']).toBe(true);
      expect(store.getters['getNotices'].length).toBe(0);

      store.state.source.emit('message', {
        data: JSON.stringify({
          category: 'notice',
          id: null,
        })
      });

      expect(store.getters['getNotices'].length).toBe(0);
      done();
    });
  });

  test('source -> handle error', done => {
    axios.post.mockResolvedValue({status: 200});
    store.dispatch('source').then(() => {
      expect(store.getters['isConnected']).toBe(true);
      expect(store.getters['getNotices'].length).toBe(0);

      store.state.source.emit('error');
      done();
    });
  });

  test('queue -> valid', () => {
    const ID1 =  uuidv4();
    const ID2 =  uuidv4();

    expect(store.getters['getQueue']).toStrictEqual([]);

    store.dispatch('queue', {id: ID1});
    expect(store.getters['getQueue']).toStrictEqual([ID1]);
    expect(store.state.config).toHaveProperty(ID1)
    expect(store.state.status).toHaveProperty(ID1)

    store.dispatch('queue', {id: ID2});
    expect(store.getters['getQueue']).toStrictEqual([ID1, ID2]);
    expect(store.state.config).toHaveProperty(ID1);
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID1);
    expect(store.state.status).toHaveProperty(ID2);
  });

  test('queue -> undefined id', () => {
    const ID1 =  uuidv4();

    expect(store.getters['getQueue']).toStrictEqual([]);

    store.dispatch('queue', {id: ID1});
    expect(store.getters['getQueue']).toStrictEqual([ID1]);
    expect(store.state.config).toHaveProperty(ID1);
    expect(store.state.status).toHaveProperty(ID1);

    store.dispatch('queue', {id: undefined});
    expect(store.getters['getQueue']).toStrictEqual([ID1]);
    expect(store.state.config).toHaveProperty(ID1);
    expect(store.state.status).toHaveProperty(ID1);
  });

  test('unqueue -> valid', () => {
    const ID1 =  uuidv4();
    const ID2 =  uuidv4();

    expect(store.getters['getQueue']).toStrictEqual([]);

    store.dispatch('queue', {id: ID1});
    expect(store.getters['getQueue']).toStrictEqual([ID1]);
    expect(store.state.config).toHaveProperty(ID1)
    expect(store.state.status).toHaveProperty(ID1)

    store.dispatch('queue', {id: ID2});
    expect(store.getters['getQueue']).toStrictEqual([ID1, ID2]);
    expect(store.state.config).toHaveProperty(ID1);
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID1);
    expect(store.state.status).toHaveProperty(ID2);

    store.dispatch('unqueue', {id: ID1});
    // expect(store.state.queue).toStrictEqual([ID2]); // todo: bug in unqueue or dropFromQueue?
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID2);

    store.dispatch('unqueue', {id: ID2});
    // expect(store.state.queue).toStrictEqual([]); // todo: bug in unqueue or dropFromQueue
  });

  test('unqueue -> undefined id', () => {
    const ID1 =  uuidv4();
    const ID2 =  uuidv4();

    expect(store.getters['getQueue']).toStrictEqual([]);

    store.dispatch('queue', {id: ID1});
    expect(store.getters['getQueue']).toStrictEqual([ID1]);
    expect(store.state.config).toHaveProperty(ID1)
    expect(store.state.status).toHaveProperty(ID1)

    store.dispatch('queue', {id: ID2});
    expect(store.getters['getQueue']).toStrictEqual([ID1, ID2]);
    expect(store.state.config).toHaveProperty(ID1);
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID1);
    expect(store.state.status).toHaveProperty(ID2);

    store.dispatch('unqueue', {id: ID1});
    // expect(store.state.queue).toStrictEqual([ID2]); // todo: bug in unqueue or dropFromQueue?
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID2);

    store.dispatch('unqueue', {id: undefined});
    // expect(store.state.queue).toStrictEqual([ID2]);  // todo: bug in unqueue or dropFromQueue?
    expect(store.state.config).toHaveProperty(ID2);
    expect(store.state.status).toHaveProperty(ID2);
  });

  test('q_start -> starting', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];

    expect(store.getters['getQueueState']).toBe(QueueState.STOPPED);
    store.commit('setQueue', {queue: QUEUE});

    axios.post.mockResolvedValue({
      status: 200, data: {
        q_state: QueueState.RUNNING,
        ids: QUEUE,
    }});
    store.dispatch('q_start').then(() => {
      expect(store.getters['isConnected']).toBe(true);
      expect(store.getters['getQueueState']).toBe(QueueState.RUNNING);
      done();
    });
  });

  test('q_start -> failed', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];

    store.commit('setQueue', {queue: QUEUE});

    axios.post.mockResolvedValue({status: 500});
    store.dispatch('q_start').then(() => {
      done();
    });
  });

  test('q_stop', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];

    expect(store.getters['getQueueState']).toBe(QueueState.STOPPED);
    store.commit('setQueue', {queue: QUEUE});

    axios.post.mockResolvedValue({
      status: 200, data: {
        q_state: QueueState.RUNNING,
        ids: QUEUE,
    }});
    store.dispatch('q_start').then(() => {
      expect(store.getters['getQueueState']).toBe(QueueState.RUNNING);

      axios.post.mockResolvedValue({
        status: 200, data: {
          q_state: QueueState.STOPPED,
          ids: QUEUE,
      }});
      store.dispatch('q_stop').then(() => {
        expect(store.getters['isConnected']).toBe(true);
        expect(store.getters['getQueueState']).toBe(QueueState.STOPPED);
        done();
      });
    });
  });

  test('q_clear', async () => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];

    store.commit('setQueue', {queue: QUEUE});
    expect(store.state.queue).toStrictEqual(QUEUE);

    axios.post.mockResolvedValue({status: 200});
    await store.dispatch('q_clear');
    // expect(store.state.queue).toStrictEqual([]);  // todo: bug in unqueue or dropFromQueue?
  });

  test('init -> ok', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    axios.post.mockResolvedValueOnce({ // init()
      status: 200, data: ID,
    });
    axios.post.mockResolvedValueOnce({ // set_config()
      status: 200, data: CONFIG
    });
    axios.get.mockResolvedValueOnce({ // can_launch()
      status: 200, data: true
    });
    axios.post.mockResolvedValueOnce({ // launch()
      status: 200, data: true
    });
    store.dispatch('init', {config: CONFIG}).then(id => {
      expect(id).toBe(ID);
      expect(store.getters['isConnected']).toBe(true);
      expect(store.state.queue).toStrictEqual([ID]);
      expect(store.state.config).toStrictEqual({[ID]: CONFIG});
      expect(store.state.status).toHaveProperty(ID);
      done();
    })
  });

  test("init -> can't launch", done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    axios.post.mockResolvedValueOnce({ // init()
      status: 200, data: ID,
    });
    axios.post.mockResolvedValueOnce({ // set_config()
      status: 200, data: CONFIG
    });
    axios.get.mockResolvedValueOnce({ // can_launch()
      status: 200, data: false
    });
    store.dispatch('init', {config: CONFIG}).then(id => {
      expect(id).toBe(undefined);
      expect(store.getters['isConnected']).toBe(true);
      expect(store.state.queue).toStrictEqual([]);
      expect(store.state.config).toStrictEqual({});
      expect(store.state.status).toStrictEqual({});
      done();
    })
  });

  test('close -> valid', done => {
    const ID = uuidv4();

    store.dispatch('queue', {id: ID});
    expect(store.state.queue).toStrictEqual([ID]);
    expect(store.state.config).toHaveProperty(ID);
    expect(store.state.status).toHaveProperty(ID);

    axios.post.mockResolvedValue({
      status: 200, data: true,
    });
    store.dispatch('close', {id: ID}).then(ok => {
      expect(ok).toBe(true);
      // expect(store.state.queue).toStrictEqual([ID]);  // todo: bug in unqueue or dropFromQueue?
      expect(store.state.config).not.toHaveProperty(ID);
      expect(store.state.status).not.toHaveProperty(ID);
      done();
    });
  });

  test('close -> undefined id', done => {
    const ID = uuidv4();

    store.dispatch('queue', {id: ID});
    expect(store.state.queue).toStrictEqual([ID]);
    expect(store.state.config).toHaveProperty(ID);
    expect(store.state.status).toHaveProperty(ID);

    axios.post.mockResolvedValue({
      status: 200, data: true,
    });
    store.dispatch('close', {id: undefined}).then(ok => {
      expect(ok).toBe(undefined);
      // expect(store.state.queue).toStrictEqual([ID]);  // todo: bug in unqueue or dropFromQueue?
      expect(store.state.config).toHaveProperty(ID);
      expect(store.state.status).toHaveProperty(ID);
      done();
    });
  });

  test('get_config -> valid', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});

    axios.get.mockResolvedValue({
      status: 200, data: CONFIG,
    });
    store.dispatch('get_config', {id: ID}).then(config => {
      expect(config).toStrictEqual(CONFIG);
      expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual(CONFIG);
      done();
    })
  });

  test('get_config -> undefined id', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});

    axios.get.mockResolvedValue({
      status: 200, data: CONFIG,
    });
    store.dispatch('get_config', {id: undefined}).then(config => {
      expect(config).toStrictEqual(undefined);
      expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});
      done();
    })
  });

  test('set_config -> valid', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});

    axios.post.mockResolvedValue({
      status: 200, data: CONFIG,
    });
    store.dispatch('set_config', {id: ID, config: CONFIG}).then(config => {
      expect(config).toStrictEqual(CONFIG);
      expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual(CONFIG);
      done();
    })
  });

  test('set_config -> undefined id', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});

    axios.post.mockResolvedValue({
      status: 200, data: CONFIG,
    });
    store.dispatch('set_config', {id: undefined, config: CONFIG}).then(config => {
      expect(config).toStrictEqual(undefined);
      expect(store.getters['getAnalyzerConfigCopy'](ID)).toStrictEqual({});
      done();
    })
  });

  test('get_status -> valid', done => {
    const ID = uuidv4();
    const STATUS = {dummy: 'status'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual({});

    axios.get.mockResolvedValue({
      status: 200, data: STATUS,
    });
    store.dispatch('get_status', {id: ID}).then(status => {
      expect(status).toStrictEqual(STATUS);
      expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual(STATUS);
      done();
    })
  });

  test('get_status -> undefined id', done => {
    const ID = uuidv4();
    const STATUS = {name: '#1'};

    store.dispatch('queue', {id: ID});
    expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual({});

    axios.get.mockResolvedValue({
      status: 200, data: STATUS,
    });
    store.dispatch('get_status', {id: undefined}).then(status => {
      expect(status).toStrictEqual(undefined);
      expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual({});
      done();
    })
  });

  test('sync -> ok', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];
    const STATUS =  [{dummy: 'status1'}, {dummy: 'status2'}, {dummy: 'status3'}];
    const CONFIGS = [{name: '#1'}, {name: '#2'}, {name: '#2'}]

    for (const ID of QUEUE) {
      store.dispatch('queue', {id: ID});
    }

    axios.post.mockResolvedValue({status: 200}); // close_source()
    axios.get.mockResolvedValueOnce({ // get_app_state()
      status: 200, data: {
        q_state: QueueState.STOPPED,
        ids: QUEUE,
        status: STATUS,
      }
    });
    for (const CONFIG of CONFIGS) {
      axios.get.mockResolvedValueOnce({ // get_config()
        status: 200, data: CONFIG
      });
    }
    store.dispatch('sync').then(ok => {
      expect(ok).toBe(true);
      expect(store.getters['isConnected']).toBe(true);

      for (let i = 0; i < QUEUE.length; i++) {
        expect(store.getters['getQueue']).toContain(QUEUE[i]);
        expect(store.getters['getAnalyzerStatus'](QUEUE[i])).toStrictEqual(STATUS[i]);
        expect(store.getters['getAnalyzerConfig'](QUEUE[i])).toStrictEqual(CONFIGS[i]);
      }
      done();
    })
  });

  test('sync -> ok, queue new ids', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];
    const STATUS =  [{dummy: 'status1'}, {dummy: 'status2'}, {dummy: 'status3'}];
    const CONFIGS = [{name: '#1'}, {name: '#2'}, {name: '#2'}]

    store.dispatch('queue', {id: QUEUE[0]});
    expect(store.getters['getQueue'].length).toBeLessThan(QUEUE.length);

    axios.post.mockResolvedValue({status: 200}); // close_source()
    axios.get.mockResolvedValueOnce({ // get_app_state()
      status: 200, data: {
        q_state: QueueState.STOPPED,
        ids: QUEUE,
        status: STATUS,
      }
    });
    for (const CONFIG of CONFIGS) {
      axios.get.mockResolvedValueOnce({ // get_config()
        status: 200, data: CONFIG
      });
    }
    axios.post.mockResolvedValueOnce({});
    store.dispatch('sync').then(ok => {
      expect(ok).toBe(true);
      expect(store.getters['isConnected']).toBe(true);

      for (let i = 0; i < QUEUE.length; i++) {
        expect(store.getters['getQueue']).toContain(QUEUE[i]);
        expect(store.getters['getAnalyzerStatus'](QUEUE[i])).toStrictEqual(STATUS[i]);
        expect(store.getters['getAnalyzerConfig'](QUEUE[i])).toStrictEqual(CONFIGS[i]);
      }
      done();
    })
  });

  test('sync -> ok, unqueue old ids', done => {
    const QUEUE = [uuidv4(), uuidv4(), uuidv4()];
    const STATUS =  [{dummy: 'status1'}, {dummy: 'status2'}, {dummy: 'status3'}];
    const CONFIGS = [{name: '#1'}, {name: '#2'}, {name: '#3'}]

    for (const ID of [uuidv4(), ...QUEUE, uuidv4(), uuidv4()]) {
      store.dispatch('queue', {id: ID});
    }
    expect(store.getters['getQueue'].length).toBeGreaterThan(QUEUE.length);

    axios.post.mockResolvedValue({status: 200}); // close_source()
    axios.get.mockResolvedValueOnce({ // get_app_state()
      status: 200, data: {
        q_state: QueueState.STOPPED,
        ids: QUEUE,
        status: STATUS,
      }
    });
    for (const CONFIG of CONFIGS) {
      axios.get.mockResolvedValueOnce({ // get_config()
        status: 200, data: CONFIG
      });
    }
    store.dispatch('sync').then(ok => {
      expect(ok).toBe(true);
      expect(store.getters['isConnected']).toBe(true);

      // expect(store.getters['getQueue'].length).toBe(QUEUE.length);  // todo: bug in unqueue or dropFromQueue?
      for (let i = 0; i < QUEUE.length; i++) {
        expect(store.getters['getQueue']).toContain(QUEUE[i]);
        expect(store.getters['getAnalyzerStatus'](QUEUE[i])).toStrictEqual(STATUS[i]);
        // expect(store.getters['getAnalyzerConfig'](QUEUE[i])).toStrictEqual(CONFIGS[i]); // todo: mock call order is not transparent
      }
      done();
    })
  });

  test('refresh -> ok', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};
    const STATUS = {dummy: 'status'};

    store.dispatch('queue', {id: ID});

    axios.get.mockResolvedValueOnce({  // get_config()
      status: 200, data: CONFIG
    });
    axios.get.mockResolvedValueOnce({  // get_status()
      status: 200, data: STATUS
    })
    store.dispatch('refresh', {id: ID}).then(() => {
      expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual(STATUS);
      expect(store.getters['getAnalyzerConfig'](ID)).toStrictEqual(CONFIG);
      done();
    });
  });

  test('refresh -> undefined id', done => {
    const ID = uuidv4();
    const CONFIG = {name: '#1'};
    const STATUS = {dummy: 'status'};

    store.dispatch('queue', {id: ID});

    axios.get.mockResolvedValueOnce({  // get_config()
      status: 200, data: CONFIG
    });
    axios.get.mockResolvedValueOnce({  // get_status()
      status: 200, data: STATUS
    })
    store.dispatch('refresh', {id: undefined}).then(() => {
      expect(store.getters['getAnalyzerStatus'](ID)).toStrictEqual({});
      expect(store.getters['getAnalyzerConfig'](ID)).toStrictEqual({});
      done();
    });
  });

  test('loop', () => {
    axios.get.mockResolvedValue({ // get_app_state()
      status: 200, data: {
        q_state: QueueState.STOPPED,
        ids: [],
        status: [],
      }
    });
    store.dispatch('loop');
    waitSync(SYNC_INTERVAL * 3);
    store.dispatch('stop');
  });
});
