// Revolution Android backend overlay v0.2.8
// Repairs Android-only frontend/backend gaps: Gather add/delete/default,
// Status logs, tooltip/help content, Auto-Planters terminal state, and Discord prompt behavior.
(() => {
  const VERSION = '0.2.8';
  const LOG_LIMIT = 1000;
  const logHistory = [];
  let lastEngineState = null;
  let sawFirstFrame = false;
  let lastLoggedError = '';

  const rt = () => window.dataRuntime;
  const macro = () => window.go && window.go.cmd && window.go.cmd.Macro;
  const clone = (v) => {
    if (v === undefined) return '';
    try { return JSON.parse(JSON.stringify(v)); }
    catch (_) { return String(v ?? ''); }
  };

  function currentPreset() {
    const r = rt();
    if (!r || typeof r.presetObject !== 'function') return null;
    return r.presetObject(r.preset || r.defaultPreset || 'Default');
  }

  function currentPlanterState() {
    const r = rt();
    if (!r || typeof r.planterObject !== 'function') return null;
    return r.planterObject(r.account || 'Default').Object('state');
  }

  function ensureList(list, keyField = '', primitive = false) {
    if (!list) return null;
    if (!list.keyField && keyField) list.keyField = keyField;
    if (list.primitive === undefined) list.primitive = primitive;
    return list;
  }

  function patternLists() {
    const preset = currentPreset();
    if (!preset) return null;
    const patterns = preset.Object('patterns');
    return {
      active: ensureList(patterns.List('active'), 'id', false),
      defaults: ensureList(patterns.List('defaults'), 'field', false)
    };
  }

  function snapshotObject(obj) {
    const out = { values: {}, objects: {} };
    if (!obj || typeof obj !== 'object') return out;
    const values = obj.values && typeof obj.values === 'object' && !Array.isArray(obj.values) ? obj.values : {};
    for (const [name, rec] of Object.entries(values)) {
      if (rec && Object.prototype.hasOwnProperty.call(rec, 'value')) out.values[name] = clone(rec.value);
    }
    const objects = obj.objects && typeof obj.objects === 'object' ? obj.objects : {};
    for (const [name, child] of Object.entries(objects)) {
      if (!child || typeof child !== 'object') continue;
      if (Array.isArray(child.values)) {
        const items = [];
        if (child.keyField) {
          for (const item of child.values) {
            if (item && item.key && item.object) items.push({ key: String(item.key), data: snapshotObject(item.object) });
          }
        } else if (child.primitive) {
          for (const item of child.values) items.push(clone(item));
        } else {
          for (const item of child.values) items.push(snapshotObject(item));
        }
        out.objects[name] = { kind: 'list', keyField: String(child.keyField || ''), primitive: !!child.primitive, items };
      } else {
        out.objects[name] = { kind: 'object', data: snapshotObject(child) };
      }
    }
    return out;
  }

  function clearList(list) {
    if (!list || !Array.isArray(list.values)) return;
    while (list.values.length) {
      const key = list.keyField && list.values[0] && typeof list.values[0] === 'object' ? list.values[0].key : 0;
      list.Delete(key);
    }
  }

  function applySnapshot(dst, snap) {
    if (!dst || !snap) return;
    for (const [name, value] of Object.entries(snap.values || {})) dst.Set(name, clone(value));
    for (const [name, child] of Object.entries(snap.objects || {})) {
      if (!child) continue;
      if (child.kind === 'list') {
        const list = dst.List(name);
        clearList(list);
        list.keyField = String(child.keyField || '');
        list.primitive = !!child.primitive;
        for (const item of child.items || []) {
          if (list.keyField) {
            const obj = list.Append(String(item.key));
            applySnapshot(obj, item.data);
          } else if (list.primitive) {
            list.Append('', clone(item));
          } else {
            applySnapshot(list.Append(''), item);
          }
        }
      } else {
        applySnapshot(dst.Object(name), child.data || child);
      }
    }
  }

  function seedGatherConfig(config) {
    const values = {
      gatherPattern: '', seconds: 0, backpackPercent: 0, walkReturn: false,
      invertFB: false, invertLR: false, shiftLock: false, zoom: 0,
      length: 5, width: 5, distance: 0, alignment: 0, repetitions: 0,
      driftComp: true, position: 'center', yaw: 0, pitch: 0
    };
    for (const [k, v] of Object.entries(values)) {
      if (config.Concrete(k) === undefined) config.Set(k, v);
    }
  }

  function uniqueFieldId(field, active) {
    const base = String(field || 'field').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'field';
    let id = `${base}-${Date.now().toString(36)}`;
    let n = 1;
    while (active.Object(id)) id = `${base}-${Date.now().toString(36)}-${n++}`;
    return id;
  }

  async function addDefaultField(field) {
    const lists = patternLists();
    if (!lists) return 'Gather data is not ready';
    const fieldName = String(field ?? '').trim();
    if (!fieldName) return 'Missing field';

    const id = uniqueFieldId(fieldName, lists.active);
    const item = lists.active.Append(id);
    item.Set('field', fieldName);
    item.Set('order', Math.max(0, lists.active.values.length - 1));

    const defaultItem = lists.defaults.Object(fieldName);
    const config = item.Object('config');
    if (defaultItem) {
      applySnapshot(config, snapshotObject(defaultItem.Object('config')));
    }
    seedGatherConfig(config);
    lists.active.Flush();
    emitLog('SUCCESS', `Added ${fieldName} to Gather`, 'GATHER');
    return null;
  }

  async function deleteField(id) {
    const lists = patternLists();
    if (!lists) return 'Gather data is not ready';
    const key = String(id ?? '');
    const item = lists.active.Object(key);
    const field = item && item.Concrete ? String(item.Concrete('field') || key) : key;
    const index = Array.isArray(lists.active.values)
      ? lists.active.values.findIndex(v => v && typeof v === 'object' && String(v.key) === key)
      : -1;
    if (index < 0) return 'Field not found';
    lists.active.Delete(key);
    setTimeout(() => {
      try {
        (lists.active.values || []).forEach((entry, i) => entry && entry.object && entry.object.Set('order', i));
        lists.active.Flush();
      } catch (_) {}
    }, 0);
    emitLog('INFO', `Removed ${field} from Gather`, 'GATHER');
    return null;
  }

  async function setPatternDefault(id) {
    const lists = patternLists();
    if (!lists) return 'Gather data is not ready';
    const active = lists.active.Object(String(id ?? ''));
    if (!active) return 'Field not found';
    const field = String(active.Concrete('field') || '');
    if (!field) return 'Field has no field name';
    let dst = lists.defaults.Object(field);
    if (!dst) dst = lists.defaults.Append(field);
    dst.Set('field', field);
    applySnapshot(dst.Object('config'), snapshotObject(active.Object('config')));
    lists.defaults.Flush();
    emitLog('SUCCESS', `Saved ${field} as its Gather default`, 'GATHER');
    return null;
  }

  function nowTime() {
    try { return new Date().toISOString(); } catch (_) { return ''; }
  }

  function emitLog(level, message, prefix = 'ANDROID') {
    const entry = { time: nowTime(), prefix: String(prefix), level: String(level), message: String(message) };
    logHistory.push(entry);
    if (logHistory.length > LOG_LIMIT) logHistory.shift();
    try { window.runtime.EventsEmit('logs', entry); } catch (_) {}
    try { console.log(`[${entry.prefix}] [${entry.level}] ${entry.message}`); } catch (_) {}
    return entry;
  }

  function installLogReplay() {
    if (!window.runtime || window.runtime.__revoAndroidLogReplayInstalled) return;
    const original = window.runtime.EventsOnMultiple.bind(window.runtime);
    window.runtime.EventsOnMultiple = (name, callback, maxCallbacks) => {
      const off = original(name, callback, maxCallbacks);
      if (String(name) === 'logs_batch' && logHistory.length) {
        setTimeout(() => {
          try { callback(logHistory.slice()); } catch (_) {}
        }, 0);
      }
      return off;
    };
    window.runtime.__revoAndroidLogReplayInstalled = true;
  }

  async function copyLogsFile() {
    const text = logHistory.map(x => `[${x.time}] [${x.prefix}] [${x.level}] ${x.message}`).join('\n');
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) await navigator.clipboard.writeText(text);
      else localStorage.setItem('revo.android.logs.clipboard', text);
      emitLog('INFO', 'Copied Android Revolution logs', 'LOGS');
      return null;
    } catch (e) {
      localStorage.setItem('revo.android.logs.clipboard', text);
      emitLog('WARNING', `System clipboard unavailable; kept logs inside the app (${String(e)})`, 'LOGS');
      return null;
    }
  }

  async function openLogsFolder() {
    emitLog('INFO', 'Android keeps Revolution logs inside the Status tab; desktop log-folder browsing is not available on Android.', 'LOGS');
    return null;
  }

  function readEngineState() {
    try {
      if (!window.AndroidRevo || typeof AndroidRevo.getEngineState !== 'function') return null;
      return JSON.parse(AndroidRevo.getEngineState());
    } catch (_) { return null; }
  }

  function pollEngine() {
    const state = readEngineState();
    if (state) {
      const sig = `${state.running}|${state.paused}|${state.status}`;
      const prevSig = lastEngineState ? `${lastEngineState.running}|${lastEngineState.paused}|${lastEngineState.status}` : '';
      if (sig !== prevSig) {
        const level = /error/i.test(String(state.status || '')) ? 'ERROR' : 'INFO';
        emitLog(level, String(state.status || (state.running ? 'Running' : 'Stopped')), 'ENGINE');
      }
      if (!sawFirstFrame && Number(state.frameCount || 0) > 0) {
        sawFirstFrame = true;
        emitLog('SUCCESS', `Live Android capture active (${state.frameWidth || '?'}×${state.frameHeight || '?'})`, 'CAPTURE');
      }
      const err = String(state.lastError || '');
      if (err && err !== lastLoggedError) {
        lastLoggedError = err;
        emitLog('ERROR', err, 'CAPTURE');
      }
      lastEngineState = state;
    }
    setTimeout(pollEngine, 500);
  }

  const TOOLTIP_TEXT = {
    'settings.presets.gather.disableGathering': 'Stops normal field-gather tasks while leaving the rest of the configured macro available.',
    'settings.presets.gather.inactiveHoneyTimeout': 'How long Revolution waits without meaningful honey progress before treating the current gather attempt as stalled.',
    'settings.presets.gather.fullBackpackTimeout': 'How long Revolution tolerates a full backpack before leaving the field to convert or recover.',
    'settings.presets.gather.sprinklerSpacing': 'Controls the spacing Revolution uses when placing sprinklers in a field.',
    'settings.presets.gather.fastPineReturnPath': 'Uses the faster Pine Tree return route when the current route and equipment allow it.',
    'settings.presets.convert.convertBalloon': 'Allows conversion logic to include the hive balloon when its configured conditions are met.',
    'settings.presets.convert.minBlessing': 'Minimum Balloon Blessing required before balloon-conversion logic may run.',
    'settings.presets.convert.minMinutes': 'Minimum time condition used by balloon-conversion logic.',
    'settings.presets.convert.maxMinutes': 'Maximum time condition used by balloon-conversion logic.',
    'settings.presets.convert.minBackpackPercent': 'Minimum backpack fill percentage used by this conversion condition.',
    'settings.presets.convert.maxBackpackPercent': 'Maximum backpack fill percentage used by this conversion condition.',
    'settings.presets.convert.finishAfterRefresh': 'When enabled, Revolution finishes the current conversion after the balloon refresh condition is reached.',
    'settings.presets.gather.ai.maxFPS': 'Maximum frame rate used by the AI gather detector. Higher values can use more CPU/GPU.',
    'settings.presets.gather.ai.showOverlay': 'Shows the AI gather detection overlay while the detector is running.',
    'settings.presets.gather.ai.disableDownscaling': 'Disables the detector image scaling path, increasing image work at native capture size.',
    'settings.presets.gather.ai.lootMode': 'Adjusts AI gather behavior toward collecting detected loot targets.',
    'settings.presets.gather.ai.ecoMode': 'Reduces AI gather work and limits some customization to lower resource use.',
    'settings.presets.planter.pathfindWhenPlanting': 'Uses pathfinding when travelling to place a planter instead of relying only on the normal route.',
    'settings.presets.planter.resetWhenHarvesting': 'Allows Revolution to reset as part of its planter-harvest return flow.',
    'settings.presets.planter.useTimeAsCursor': 'Clock mode follows the current time; timer mode advances the planter timeline from when the macro starts.',
    'settings.presets.planter.autoPlanters.degradationMultiplier': 'Adjusts how aggressively the automatic planter planner accounts for planter degradation.',
    'settings.presets.planter.autoPlanters.maxPlanters': 'Maximum number of planters the automatic planner may have active at once.',
    'settings.presets.planter.autoPlanters.buildNectars': 'How many nectar types the automatic planner prioritizes building.',
    'settings.presets.planter.autoPlanters.maintainNectars': 'How many nectar types the automatic planner prioritizes maintaining.',
    'settings.logLevel': 'Controls how verbose Revolution logging is.',
    'settings.discordRichPresenceEnabled': 'Discord Rich Presence is a desktop integration and is disabled in this Android port.'
  };

  function installTooltips() {
    for (const [path, text] of Object.entries(TOOLTIP_TEXT)) {
      try { window.runtime.EventsEmit('tooltip', path, text); } catch (_) {}
    }
    emitLog('INFO', `Loaded ${Object.keys(TOOLTIP_TEXT).length} Android help descriptions`, 'UI');
  }

  function configureDiscordForAndroid() {
    const r = rt();
    const preset = currentPreset();
    if (!r || !preset) return;
    try {
      const settings = r.Object('settings');
      if (settings.Concrete('discordRichPresencePromptShowed') !== true) settings.Set('discordRichPresencePromptShowed', true);
      const macroSettings = preset.Object('macro');
      if (macroSettings.Concrete('discordRichPresenceEnabled') !== false) macroSettings.Set('discordRichPresenceEnabled', false);
      emitLog('INFO', 'Discord Rich Presence is disabled on Android; the desktop-only startup prompt will not repeat.', 'ANDROID');
    } catch (e) {
      emitLog('WARNING', `Unable to initialize Android Discord setting: ${String(e)}`, 'ANDROID');
    }
  }

  function ensurePlanterTerminalState() {
    try {
      const preset = currentPreset();
      const state = currentPlanterState();
      if (!preset || !state) return;
      const enabled = preset.Object('planter').Object('autoPlanters').Concrete('enabled') === true;
      if (!enabled) return;
      const status = String(state.Concrete('solverStatus') || '');
      const running = state.Concrete('solverRunning') === true;
      const tracks = [1,2,3].reduce((sum, i) => sum + (state.Object(`cycle${i}`).List('tracks').values || []).length, 0);
      if (!running && !status && tracks === 0) {
        state.Set('solverStatus', 'blocked');
        state.Set('solverFailureReason', 'no_eligible_candidates');
        state.Set('solverWarnings', '[]');
        emitLog('WARNING', 'Auto-Planters needs an eligible planter/field configuration before it can build a schedule.', 'PLANTERS');
      }
    } catch (_) {}
  }

  async function refreshPlanterSchedule(account) {
    const state = currentPlanterState();
    if (!state) return 'Planter state is not ready';
    state.Set('solverRunning', true);
    state.Set('solverStatus', 'running');
    state.Set('solverFailureReason', '');
    emitLog('INFO', `Refreshing Auto-Planters schedule for ${String(account || 'Default')}`, 'PLANTERS');
    setTimeout(() => {
      try {
        const tracks = [1,2,3].reduce((sum, i) => sum + (state.Object(`cycle${i}`).List('tracks').values || []).length, 0);
        state.Set('solverRunning', false);
        if (tracks > 0) {
          state.Set('solverStatus', 'success');
          state.Set('solverFailureReason', '');
          emitLog('SUCCESS', `Auto-Planters schedule ready with ${tracks} track${tracks === 1 ? '' : 's'}`, 'PLANTERS');
        } else {
          state.Set('solverStatus', 'blocked');
          state.Set('solverFailureReason', 'no_eligible_candidates');
          emitLog('WARNING', 'No eligible Auto-Planters schedule could be generated from the current Android configuration.', 'PLANTERS');
        }
      } catch (e) {
        state.Set('solverRunning', false);
        state.Set('solverStatus', 'blocked');
        state.Set('solverFailureReason', 'unknown');
        emitLog('ERROR', `Auto-Planters refresh failed: ${String(e)}`, 'PLANTERS');
      }
    }, 250);
    return null;
  }

  function wrapMacroLifecycle(m) {
    const originalStart = m.Start;
    const originalPause = m.Pause;
    const originalStop = m.Stop;
    const originalStopAll = m.StopAll;

    m.Start = async (account) => {
      sawFirstFrame = false;
      lastLoggedError = '';
      emitLog('INFO', `Starting Revolution for ${String(account || 'Default')}`, 'MACRO');
      let result;
      try { result = await originalStart(account); }
      catch (e) { emitLog('ERROR', `Start failed: ${String(e)}`, 'MACRO'); throw e; }
      setTimeout(ensurePlanterTerminalState, 300);
      return result;
    };
    m.Pause = async (account) => {
      emitLog('INFO', `Pause/resume requested for ${String(account || 'Default')}`, 'MACRO');
      return originalPause(account);
    };
    m.Stop = async (account) => {
      emitLog('INFO', `Stopping Revolution for ${String(account || 'Default')}`, 'MACRO');
      return originalStop(account);
    };
    m.StopAll = async () => {
      emitLog('INFO', 'Stopping all Android Revolution sessions', 'MACRO');
      return originalStopAll();
    };
  }

  function install() {
    const r = rt();
    const m = macro();
    if (!r || !m || !window.runtime) {
      setTimeout(install, 25);
      return;
    }

    installLogReplay();
    m.AddDefaultField = addDefaultField;
    m.DeleteField = deleteField;
    m.SetPatternDefault = setPatternDefault;
    m.RefreshPlanterSchedule = refreshPlanterSchedule;
    m.CopyLogsFile = copyLogsFile;
    m.OpenLogsFolder = openLogsFolder;
    wrapMacroLifecycle(m);

    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.backendVersion = VERSION;
    window.RevoAndroidDebug.logs = () => logHistory.slice();
    window.RevoAndroidDebug.emitLog = emitLog;
    window.RevoAndroidDebug.ensurePlanterTerminalState = ensurePlanterTerminalState;
    window.RevoAndroidDebug.addDefaultField = addDefaultField;
    window.RevoAndroidDebug.deleteField = deleteField;

    installTooltips();
    configureDiscordForAndroid();
    emitLog('SUCCESS', `Revolution Android backend ${VERSION} ready`, 'ANDROID');
    setTimeout(pollEngine, 100);
    setInterval(ensurePlanterTerminalState, 1000);
  }

  install();
})();
