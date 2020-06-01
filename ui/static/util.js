export async function fileExists(path) {
  // todo: deprecated?
  let http = new XMLHttpRequest();
  http.open("HEAD", path, false);
  http.send().then(response => {
    return response.status !== 404;
  });
}

export function decodeWebpackString(webpack_string, encoding = "utf-8") {
  /* Convert a string included in a Webpack plugin into a useable string */

  return new TextDecoder(encoding).decode(
    // todo: this is not super performant
    Buffer.from(Object.values(webpack_string))
  );
}

export function seconds2timestr(seconds, format = "") {
  /* https://stackoverflow.com/a/25279399/12259362 */
  var date = new Date(0);
  date.setSeconds(seconds, (seconds % 1) * 1000);
  return date.toISOString().substr(14, 8);
}
