import pointer from "json-pointer";

export function seconds2timestr(seconds, format = "") {
  /* https://stackoverflow.com/a/25279399/12259362 */
  var date = new Date(0);
  date.setSeconds(seconds, (seconds % 1) * 1000);
  return date.toISOString().substr(14, 7);
}

export function uuidv4() {
  // https://stackoverflow.com/a/2117523/12259362
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
    var r = (Math.random() * 16) | 0,
      v = c == "x" ? r : (r & 0x3) | 0x8;
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
