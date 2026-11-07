#!/usr/bin/env node
'use strict';
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');

const [, , backendFile, planFile] = process.argv;
if (!backendFile || !planFile) throw new Error('usage: node test_android_frontend_plan.cjs BACKEND.js PLAN.json');
const src = fs.readFileSync(backendFile, 'utf8');
const plan = JSON.parse(fs.readFileSync(planFile, 'utf8'));
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };

function makeHarness(stored, opts={}) {
  const calls = { configured: [], starts: [] };
  const selectedConfig = {
    Concrete(name) {
      const table = {gatherPattern: opts.patternName || 'e_lol', width: 2,
        length: 8, repetitions: 0, alignment: 0};
      return table[name];
    },
  };
  const entry = {
    object: {
      Concrete(key) {return key === 'field' ? 'Sunflower' : key === 'order' ? 0 : null;},
      Object() {return selectedConfig;}
    }
  };
  const preset = {
    Object(name) {
      if (name === 'patterns') return {List() {return {values: opts.noEntry ? [] : [entry]};}};
      if (name === 'macro') return {Concrete() {return 50;}};
      if (name === 'player') return {Concrete() {return 24;}};
      throw new Error('unexpected preset object '+name);
    },
  };
  const macro = {Start: async function(account) {calls.starts.push(account);return 'started';}};
  const android = {
    configureMacro(json) {
      calls.configured.push(JSON.parse(json));
      return JSON.stringify(opts.nativeState || {patternStepCount: 18, lastDecision:'configured:e_lol:18'});
    }
  };
  const runtime = {preset:'Default', defaultPreset:'Default', presetObject: () => preset};
  const window = {AndroidRevo:android, go:{cmd:{Macro:macro}}, dataRuntime:runtime, RevoAndroidDebug:{}};
  const localStorage = {getItem(key) {return key==='revo.research.actionPlanV1'?stored:null;}};
  const silentConsole = {log(){}, error(){}};
  vm.runInNewContext(src,{window,AndroidRevo:android,localStorage,
    setTimeout() {},console:silentConsole});
  return {macro,calls,window};
}

async function mustNotStart(stored, opts={}) {
  const h=makeHarness(stored,opts);
  await assert.rejects(h.macro.Start('Default'));
  check(h.calls.starts.length===0,'rejected plan launched Roblox');
  return h;
}

async function main() {
  let h=makeHarness(null);
  await h.macro.Start('Default');
  check(h.calls.configured.length===1,'legacy config did not run');
  check(!h.calls.configured[0].enablePlannedExecution,'legacy startup accidentally enabled a plan');
  check(h.calls.starts.length===1,'legacy original Start not invoked');

  h=makeHarness(JSON.stringify({enabled:true,plan}));
  await h.macro.Start('Default');
  check(h.calls.configured.length===1,'opt-in config did not run');
  check(h.calls.configured[0].enablePlannedExecution===true,'opt-in execution flag missing');
  check(h.calls.configured[0].actionPlan.actions.length===18,'native plan not passed');
  check(h.calls.starts.length===1,'authorized plan did not call native start');

  h=await mustNotStart(JSON.stringify({enabled:true,plan}),{patternName:'CornerXSnake'});
  check(h.calls.configured.length===0,'mismatched pattern was dispatched');

  h=await mustNotStart(JSON.stringify({enabled:true,plan:{...plan,movementMsPerStud:50}}));
  check(h.calls.configured.length===0,'mismatched timing was dispatched');

  h=await mustNotStart('{invalid-json');
  check(h.calls.configured.length===0,'invalid saved plan was dispatched');

  h=await mustNotStart(JSON.stringify({enabled:true,plan}),{noEntry:true});
  check(h.calls.configured.length===0,'plan launched with no Gather row');

  h=await mustNotStart(JSON.stringify({enabled:true,plan}),{
    nativeState:{lastDecision:'configure-error',patternStepCount:0}});
  check(h.calls.configured.length===1,'native failure was not reached');

  h=makeHarness(JSON.stringify({enabled:false,plan:{...plan,pattern:'not-selected'}}));
  await h.macro.Start('Default');
  check(!h.calls.configured[0].enablePlannedExecution,'explicitly disabled plan was applied');
  check(h.calls.starts.length===1,'disabled-plan legacy path broke');

  console.log('PASS: React/Wails frontend research plan gating, '+checks+' assertions');
}
main().catch(e=>{console.error(e.stack||String(e));process.exitCode=1;});
