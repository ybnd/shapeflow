import axios from 'axios';

let BACKEND_ROOT = 'http://localhost:7951';  // todo: something something .env   https://stackoverflow.com/questions/49257650/
                                             //       but also need to use CORS...

let API = BACKEND_ROOT + '/api/';
let DB = BACKEND_ROOT + '/db/';
let STREAM = BACKEND_ROOT + '/stream/';

export function url_api (id, endpoint, method = '') {
  if (method === '') {
    return API + `${id}/${endpoint}`
  } else {
    return API + `${id}/${endpoint}/${method}`
  }

}
export function url_db (id, endpoint = '') {
  return DB + `${id}/${endpoint}`
}
export function url_stream (id, endpoint) {
  return STREAM + `${id}/${endpoint}`
}

// define analyzer state Enum
export const analyzer_state = {
  unset: 0,
  INCOMPLETE: 1,
  LAUNCHED: 2,
  RUNNING: 3,
  CANCELED: 4,
  ERROR: 5,
};


export function ping () {
  axios.get(API + 'ping');  //todo: some indicator that pings are not coming through?
}

export function unload () {
  // axios can't be called on page unload, use sendBeacon instead
  return navigator.sendBeacon(API + 'unload');
}
export function list () {
  await axios.get(API + 'list');
}


export async function init () {
  // initialize an Analyzer in the backend & return its id
  axios.post(API + 'init')
    .then((response) => {
      if (response.status === 200) {
        return response.data;
      }
    }
  );
}

export async function get_schemas (id) {
  await axios.get(url_api(id, 'schemas'))
    .then((response) => {
      if (response.status === 200) {
        return response.data;
      }
    }
  );
}

export async function get_config (id) {
  let response = await axios.get(url_api(id, 'get_config'));
  if (response.status === 200) {
    return response.data;
  }
}

export async function set_config (id, config) {
  let response = await axios.post(url_api(id, 'set_config'), config);
  if (response.status === 200) {
    return true;
  }
}

export async function launch (id) {
  let response1 = await axios.get(url_api(id, 'can_launch'));
  if (response1.data) {
    let response2 = await axios.put(url_api(id, 'launch'));
    if (response2.status === 200) {
      return true;
    }
  }
}
