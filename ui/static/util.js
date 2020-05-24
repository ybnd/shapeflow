export async function fileExists(path) {
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
