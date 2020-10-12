import {execSync, spawn} from "child_process";

export function waitSync(ms) {
  const end = Date.now() + ms;
  while (Date.now() < end) {}
}

export function startServer() {
  const SERVER = spawn(
    'python3', ['shapeflow.py', '--server'],
    {cwd: '..', shell: false, detached: false}
  );
  waitSync(2000);
  return SERVER;
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
    execSync(`pkill -f "python3 shapeflow.py"`);
    waitSync(2000);
  } catch(e) {
    //console.warn(e.message);
  }
}
