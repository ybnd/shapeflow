import Vue from 'vue'
import axios from 'axios'
import { uuidv4 } from '~/static/util'

export const state = () => ({
  init: true,
  ids: [],
  analyzers: {},
  current: {
    id: '',
  },
  launched: {},
  return: {
    id: '',
  },
  last_id: '',
});

export const mutations = {
  async init (state, id = '') {
    if (id === '') {
      id = uuidv4();
    }
    state.last_id = id;
    await axios.get(`/api/init/${id}`);
    let response = await axios.get(`/api/${id}/schemas`);
    if (response.status === 200){
      console.log(response);
      var schemas = response.data;
      Vue.set(
        state.analyzers, id, {
          "schemas": schemas,
      }
      );
    }

  },
  setCurrent (state, id) {
    state.current = state.analyzers[id];
  },
  async list (state) {
    var response = await axios.get('/api/list');
    var ids = response.data;
    for (var i = 0; i < ids.length; i++) {
      if (!state.ids.includes(ids[i])) {
        state.ids.push(ids[i]);
      }
    }
    console.log(state.ids)
  },
  async launch (state, id = '') {
    if (id === ''){
      id = state.last_id;
    }
    if (await axios.get(`/api/${id}/can_launch`)) {
      axios.get(`/api/${id}/launch`);
    }
  },
};

export const actions = {
  async newAnalyzer({commit}, id = '') {
    commit('init', id);
  },
};
