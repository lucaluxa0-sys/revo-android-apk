#!/usr/bin/env node
'use strict';

const fs = require('fs');
const vm = require('vm');

const patchPath = process.argv[2];
if (!patchPath) throw new Error('usage: verify-v0212-ui-lifecycle.js <lifecycle-patch.js>');
const source = fs.readFileSync(patchPath, 'utf8');

let clock = 1000;
let engine = { running: false, paused: false, status: 'Stopped' };
let startCalls = 0;
let pauseCalls = 0;
let stopCalls = 0;
let stopAllCalls = 0;
const timers = [];
const values = new Map();
const updates = [];

function key(account, field) { return `${account}.${field}`; }
function stateObject(account) {
  const name = String(account || 'Default');
  return {
    Set(field, value) {
      values.set(key(name, field), value);
      updates.push([name, field, value]);
    },
    Concrete(field) { return values.get(key(name, field)); }
  };
}

const macro = {
  Start: async () => { startCalls += 1; },
  Pause: async () => { pauseCalls += 1; },
  Stop: async () => { stopCalls += 1; },
  StopAll: async () => { stopAllCalls += 1; }
};

const context = {
  console,
  Date: class extends Date { static now() { return clock; } },
  window: {
    dataRuntime: { account: 'Default', stateObject },
    runtime: {
      EventsEmit(name, path, _id, value) {
        if (name !== 'set') throw new Error(`unexpected event ${name}`);
        const m = /^state\.macros\[([^\]]+)\]\.([^.]+)$/.exec(String(path));
        if (!m) throw new Error(`unexpected lifecycle path ${path}`);
        values.set(key(m[1], m[2]), value);
        updates.push([m[1], m[2], value]);
      }
    },
    go: { cmd: { Macro: macro } },
    AndroidRevo: null,
    RevoAndroidDebug: {}
  },
  setTimeout(fn, ms) { timers.push({ fn, ms }); return timers.length; },
  clearTimeout() {}
};
context.AndroidRevo = context.window.AndroidRevo = {
  getEngineState: () => JSON.stringify(engine)
};
vm.createContext(context);
vm.runInContext(source, context, { filename: patchPath });

function assert(cond, msg) { if (!cond) throw new Error(`FAIL: ${msg}`); }
function val(field) { return values.get(key('Default', field)); }
function runPoll() {
  const index = timers.findIndex(item => Number(item.ms || 0) === 200);
  assert(index >= 0, 'expected a scheduled lifecycle poll');
  const [item] = timers.splice(index, 1);
  clock += Number(item.ms || 0);
  item.fn();
}

(async () => {
  assert(val('running') === false, 'initial native stopped state must sync running=false');
  assert(val('paused') === false, 'initial native stopped state must sync paused=false');

  await macro.Start('Default');
  assert(startCalls === 1, 'first Start must invoke native bridge exactly once');
  assert(val('running') === true, 'Start must optimistically set running=true immediately');
  assert(val('status') === 'Starting', 'Start must expose Starting while native launch settles');

  await macro.Start('Default');
  assert(startCalls === 1, 'duplicate Start during startup must be ignored');

  runPoll();
  assert(val('running') === true, 'pre-native startup poll must keep Start locked');

  engine = { running: true, paused: false, status: 'Gathering' };
  runPoll();
  assert(val('running') === true && val('status') === 'Gathering', 'native running state must become authoritative');

  await macro.Start('Default');
  assert(startCalls === 1, 'Start while native running must be ignored');

  await macro.Pause('Default');
  assert(pauseCalls === 1, 'Pause must invoke native bridge once while running');
  engine = { running: true, paused: true, status: 'Paused' };
  runPoll();
  assert(val('paused') === true && val('status') === 'Paused', 'native paused state must sync to frontend');

  // Resume is represented by Start in the desktop frontend when paused. Preserve
  // that existing bridge behavior while still blocking duplicate running starts.
  await macro.Start('Default');
  assert(startCalls === 2, 'Start while paused must preserve resume behavior');
  engine = { running: true, paused: false, status: 'Gathering' };
  runPoll();
  await macro.Stop('Default');
  assert(stopCalls === 1, 'Stop must invoke native bridge once');
  assert(val('running') === true && val('status') === 'Stopping', 'Stop must keep Start disabled until native confirms stopped');
  await macro.Stop('Default');
  assert(stopCalls === 1, 'duplicate Stop while stopping must be ignored');

  runPoll();
  assert(val('running') === true, 'poll while native still running must keep Start disabled');
  engine = { running: false, paused: false, status: 'Stopped' };
  runPoll();
  assert(val('running') === false && val('status') === 'Stopped', 'native stop confirmation must re-enable Start');

  // Native/remote starts must also be reflected in the desktop-derived UI.
  engine = { running: true, paused: false, status: 'Remote running' };
  runPoll();
  assert(val('running') === true && val('status') === 'Remote running', 'remote/native start must synchronize to UI');

  engine = { running: false, paused: false, status: 'Stopped' };
  runPoll();
  assert(val('running') === false, 'remote/native stop must synchronize to UI');

  // Stop during startup must be accepted even before native flips running=true.
  await macro.Start('Default');
  assert(startCalls === 3, 'fresh Start after confirmed stop must be allowed');
  await macro.Stop('Default');
  assert(stopCalls === 2, 'Stop during starting grace must be allowed');

  // StopAll follows the same single-transition guard.
  engine = { running: false, paused: false, status: 'Stopped' };
  runPoll();
  engine = { running: true, paused: false, status: 'Running' };
  runPoll();
  await macro.StopAll();
  assert(stopAllCalls === 1, 'StopAll must invoke native bridge exactly once');
  await macro.StopAll();
  assert(stopAllCalls === 1, 'duplicate StopAll must be ignored');

  assert(updates.length > 0, 'expected runtime lifecycle updates');
  console.log(`PASS: lifecycle UI/native bridge start=${startCalls} pause=${pauseCalls} stop=${stopCalls} stopAll=${stopAllCalls} updates=${updates.length}`);
})().catch(err => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
