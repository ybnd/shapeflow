import {execSync, spawn, kill} from "child_process";

export function waitSync(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {}
}

export function startServer() {
  const SERVER = spawn(
    'python3', ['sf.py', '--background'],
    {cwd: '..', shell: false, detached: false}
  );
  SERVER.unref();
  waitSync(2000);
}

export function checkIfListening() {
  try {
    execSync(`ss -tulwp | grep 7951`);
    return true;
  } catch(e) {
    return false;
  }
}

export function killServer() {
  try {
    execSync(`pgrep -f "python3 sf" | xargs -I $ kill -9 $`);
    waitSync(2000);
  } catch(e) {
    //console.warn(e.message);
  }
}
