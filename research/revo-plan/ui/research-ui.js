/* Revo research-preview controls: user-initiated; no autostart or hidden gameplay input. */
(() => {
  'use strict';
  const id = name => document.getElementById(name);
  const state = {plan: null, native: null, error: ''};
  const dirs = new Set(['FORWARD', 'BACKWARD', 'LEFT', 'RIGHT']);
  const native = () => window.AndroidRevo || null;

  function checkPlan(plan) {
    if (!plan || plan.schema !== 'revo.action-plan.v1' ||
        plan.dryRunOnly !== true || !/^[0-9a-f]{64}$/.test(String(plan.sourceSha256 || ''))) {
      throw new Error('Not a source-identified Revo movement plan.');
    }
    if (typeof plan.pattern !== 'string' || !/^[A-Za-z][A-Za-z0-9_]{0,49}$/.test(plan.pattern)) {
      throw new Error('Invalid pattern identifier.');
    }
    const speed = plan.movementMsPerStud;
    if (!Number.isFinite(speed) || speed <= 0 || speed > 1000) {
      throw new Error('Invalid movement calibration.');
    }
    if (!Array.isArray(plan.actions) || plan.actions.length === 0 || plan.actions.length > 512) {
      throw new Error('Expected 1–512 bounded movement actions.');
    }
    let durationSum = 0;
    for (const [i, step] of plan.actions.entries()) {
      if (!step || step.type !== 'walk' || !dirs.has(step.direction) ||
          !Number.isFinite(step.studs) || step.studs <= 0 || step.studs > 160) {
        throw new Error('Unsupported movement at step '+(i+1)+'.');
      }
      const expected = Math.max(50, Math.round(step.studs * speed));
      if (expected > 10000 || step.durationMs !== expected) {
        throw new Error('Duration mismatch at step '+(i+1)+'.');
      }
      durationSum += expected;
    }
    if (durationSum > 15 * 60 * 1000) {
      throw new Error('Plan exceeds 15 minutes of unbroken motion.');
    }
    // This preview is intentionally limited to the source-checked width-2 e_lol route.
    const expected = [['LEFT',10],
      ['BACKWARD',20],['RIGHT',5],['FORWARD',20],['RIGHT',5],
      ['BACKWARD',20],['RIGHT',5],['FORWARD',20],['RIGHT',5],
      ['BACKWARD',20],['LEFT',5],['FORWARD',20],['LEFT',5],
      ['BACKWARD',20],['LEFT',5],['FORWARD',20],['LEFT',5],['RIGHT',10]];
    const executable = plan.pattern === 'e_lol' &&
      plan.sourceSha256 === '042c8989b87e8faf109ffb54a7ea9b41f516c4652c9947592b467e4ca943648c' &&
      plan.actions.length === expected.length &&
      plan.actions.every((step,i)=>step.direction===expected[i][0] && step.studs===expected[i][1]);
    return {count: plan.actions.length, totalMs: durationSum, executable};
  }

  function makeConfig(plan, account) {
    const inspection = checkPlan(plan);
    // Only e_lol + Sunflower has a source-grounded pre-gather route here.
    if (!inspection.executable) throw new Error('Only Sunflower / e_lol is routed in this preview.');
    if (typeof account !== 'string' || !/^[A-Za-z0-9 _-]{1,50}$/.test(account)) {
      throw new Error('Invalid account name.');
    }
    return {
      routine: 'gather', account, field: 'sunflower',
      patternName: 'e_lol', width: 2, length: 8,
      repetitions: 0, alignment: 0, keyDelayMs: 50,
      msPerStud: plan.movementMsPerStud,
      requireRobloxForeground: true,
      actionPlan: plan,
      enablePlannedExecution: true
    };
  }

  function say(message, category) {
    const feedback=id('notice');
    feedback.textContent=String(message);
    feedback.className='feedback'+(category?' '+category:'');
    state.error=category === 'error' ? String(message) : '';
  }

  function inspectInput() {
    state.plan=null;
    id('authorize').checked=false;
    let plan;
    try {
      plan=JSON.parse(id('plan-input').value);
      const info=checkPlan(plan);
      state.plan=plan;
      id('plan-badge').textContent=info.executable?'Ready to authorize':'Offline-plan only';
      id('plan-summary').textContent=info.count+' steps · '+Math.ceil(info.totalMs/1000)+' s movement';
      if (info.executable) say('Plan validated. Check authorization to enable Start.','ok');
      else say('This plan is readable, but no live field route is supported for it.');
    } catch (e) {
      id('plan-badge').textContent='Invalid plan';
      id('plan-summary').textContent='';
      say(String(e.message || e),'error');
    }
    updateControls();
  }

  function engineState() {
    const bridge=native();
    if (!bridge || typeof bridge.getEngineState !== 'function') return null;
    try {
      const raw=bridge.getEngineState();
      return typeof raw==='string'?JSON.parse(raw||'{}'):(raw||{});
    } catch (e) {
      return {lastError:'Engine state unavailable: '+String(e)};
    }
  }

  function updateControls() {
    const bridge=native();
    let ready=false;
    try {ready=Boolean(bridge && bridge.accessibilityReady());}catch(_){}
    const selected=state.plan && state.plan.pattern==='e_lol';
    id('start').disabled=!(ready && selected && id('authorize').checked);
    const active=Boolean(state.native && state.native.running);
    id('pause').disabled=!active;
    id('status').textContent=JSON.stringify(state.native || {androidBridge:!!bridge, accessibilityReady:ready},null,2);
    return ready;
  }

  function refresh() {
    state.native=engineState();
    updateControls();
  }

  async function loadSample() {
    try {
      const response=await fetch('revo-plans/e_lol.json',{cache:'no-store'});
      if (!response.ok) throw new Error('Sample unavailable (HTTP '+response.status+')');
      id('plan-input').value=await response.text();
      inspectInput();
    } catch (e) {
      say('Could not load included sample: '+String(e),'error');
    }
  }

  function start() {
    if (!state.plan || !id('authorize').checked || id('start').disabled) {
      say('Validate the supported plan, enable Accessibility, and authorize first.','error');return;
    }
    try {
      const bridge=native();
      if (!bridge || typeof bridge.configureMacro!=='function' ||
          typeof bridge.startMacroAndRoblox!=='function' || !bridge.accessibilityReady()) {
        throw new Error('Android native bridge or Accessibility is unavailable.');
      }
      const cfg=makeConfig(state.plan,id('account').value.trim());
      const result=JSON.parse(bridge.configureMacro(JSON.stringify(cfg))||'{}');
      if (result.lastDecision==='configure-error' ||
          result.patternName !==cfg.patternName ||
          Number(result.patternStepCount)!==cfg.actionPlan.actions.length) {
        throw new Error('Native engine rejected the plan (no launch performed).');
      }
      if (bridge.startMacroAndRoblox(cfg.account)!==true) {
        throw new Error('Bee Swarm launch request was not accepted.');
      }
      say('Bee Swarm launch requested. Check Roblox and the live movement evidence.','ok');
      refresh();
    } catch(e) {
      say('Start refused: '+String(e.message||e),'error');
      refresh();
    }
  }

  function stop() {
    try {const b=native();if(!b)throw new Error('bridge unavailable');
      b.stopAll(); say('Stop requested.','ok');refresh();
    } catch(e){say('Stop failed: '+String(e),'error');}
  }
  function pause() {
    try {const b=native();if(!b)throw new Error('bridge unavailable');
      b.pauseMacro(id('account').value.trim()||'Default');say('Pause/resume requested.');refresh();
    } catch(e){say('Pause failed: '+String(e),'error');}
  }
  function accessibility() {
    try {const b=native();if(!b)throw new Error('bridge unavailable');
      b.openAccessibilitySettings();
    }catch(e){say('Cannot open Accessibility settings: '+String(e),'error');}
  }
  function init() {
    id('load-sample').addEventListener('click',loadSample);
    id('validate').addEventListener('click',inspectInput);
    id('plan-input').addEventListener('input',()=>{state.plan=null;id('authorize').checked=false;updateControls();});
    id('authorize').addEventListener('change',updateControls);
    id('start').addEventListener('click',start);
    id('stop').addEventListener('click',stop);
    id('pause').addEventListener('click',pause);
    id('accessibility').addEventListener('click',accessibility);
    id('refresh').addEventListener('click',refresh);
    refresh();
    setInterval(refresh,1500);
  }
  window.RevoResearchUI={checkPlan,makeConfig}; // Pure policy helpers for isolated tests.
  document.addEventListener('DOMContentLoaded',init);
})();
