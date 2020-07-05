export function seconds2timestr(seconds, format = "") {
  /* https://stackoverflow.com/a/25279399/12259362 */
  var date = new Date(0);
  date.setSeconds(seconds, (seconds % 1) * 1000);
  return date.toISOString().substr(14, 7);
}
