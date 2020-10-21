import pointer from "json-pointer";
import assert from 'assert';

export function seconds2timestr(seconds) {
  /* https://stackoverflow.com/a/25279399/12259362 */
  assert(Number.isFinite(seconds))

  var date = new Date(0);
  date.setSeconds(seconds, (seconds % 1) * 1000);
  return date.toISOString().substr(14, 7);
}

export function uuidv4() {
  // https://stackoverflow.com/a/2117523/12259362
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0,
      v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export function get_reference(subschema) {
  if (subschema.hasOwnProperty("$ref")) {
    return subschema.$ref;
  } else if (subschema.hasOwnProperty("allOf")) {
    return subschema.allOf[0].$ref;
  } else if (subschema.hasOwnProperty("items")) {
    return subschema.items.$ref;
  } else {
    return undefined;
  }
}

export function dereference(schema, reference) {
  return pointer.get(
    schema,
    reference.slice(1) // '#/definitions/<reference>' --> '/definitions/<reference>'
  );
}

export function splitlines(text) {
  return text.match(/[^\r\n]+/g)
}

export async function retryOnce(method, arg) {
  return method(arg).then(out => {
    return out;
  }).catch(() => {
    return method(arg).then(out => {
      return out;
    })
  })
}


// For making <b-popover> render properly in JSDOM
// https://github.com/bootstrap-vue/bootstrap-vue/blob/515ae63f87c9a03c86d63fd49b28df4e98ebac54/tests/utils.js#L3

export function createContainer(tag = 'div') {
  const container = document.createElement(tag)
  document.body.appendChild(container)
  return container
}

export function bPopoverJsDomHack() {
  // https://github.com/FezVrasta/popper.js/issues/478#issuecomment-407422016
  // Hack to make Popper not bork out during tests
  // Note popper still does not do any positioning calculation in JSDOM though
  // So we cannot test actual positioning, just detect when it is open
  document.createRange = () => ({
    setStart: () => {
    },
    setEnd: () => {
    },
    commonAncestorContainer: {
      nodeName: 'BODY',
      ownerDocument: document
    }
  })
  // Mock `getBoundingClientRect()` so that the `isVisible(el)` test returns `true`
  // Needed for visibility checks of trigger element, etc
  Element.prototype.getBoundingClientRect = jest.fn(() => ({
    width: 24,
    height: 24,
    top: 0,
    left: 0,
    bottom: 0,
    right: 0
  }))
}
