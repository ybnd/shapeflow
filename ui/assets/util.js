export async function fileExists(path) {
  let http = new XMLHttpRequest();
  http.open("HEAD", path, false);
  http.send().then(response => {
    return response.status !== 404;
  });
}
a;
