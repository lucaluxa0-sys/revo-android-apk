// Revolution Android backend overlay v0.2.10
// Restores the real Gather pattern catalog expected by the desktop frontend.
(() => {
  const VERSION = '0.2.10';

  // Exact SetName(...) values recovered from the pinned Revolution desktop
  // v0.9c-hotfix3 runtime gather Lua files. Keep this list desktop-grounded.
  const BUILTIN_GATHER_PATTERNS = Object.freeze([
    'Bamboo',
    'BambooAlt',
    'BestCactus',
    'BlueFlower',
    'BlueFlowerAlt',
    'Bowl',
    'CornerXSnake',
    'e_lol',
    'hivehubloot',
    'hivehubloot2',
    'Kettle',
    'kettletopleft',
    'PineAlt',
    'Skillet',
    'tidal_surge'
  ]);

  function runtime() {
    return window.dataRuntime || null;
  }

  function availablePatternList() {
    const rt = runtime();
    if (!rt || typeof rt.Object !== 'function') return null;
    try {
      const list = rt.Object('state').Object('config').List('availablePatterns');
      // The desktop frontend consumes this as a primitive string list.
      list.primitive = true;
      list.keyField = '';
      return list;
    } catch (e) {
      console.error('[android-patterns] failed to resolve availablePatterns', String(e));
      return null;
    }
  }

  function currentNames(list) {
    const values = Array.isArray(list && list.values) ? list.values : [];
    return values.filter(v => typeof v === 'string' && v.length > 0);
  }

  function repairAvailablePatterns(reason) {
    const list = availablePatternList();
    if (!list || typeof list.Append !== 'function') return false;

    const existing = currentNames(list);
    const seen = new Set(existing);
    let added = 0;

    // Preserve anything a newer desktop/backend source has already supplied.
    // Only backfill missing names from the exact pinned desktop runtime.
    for (const name of BUILTIN_GATHER_PATTERNS) {
      if (seen.has(name)) continue;
      list.Append('', name);
      seen.add(name);
      added += 1;
    }

    const finalNames = currentNames(list);
    console.log(
      `[android-patterns] ${reason || 'repair'} existing=${existing.length} added=${added} final=${finalNames.length}`
    );
    return finalNames.length > 0;
  }

  function pinDebugVersion() {
    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    try {
      Object.defineProperty(window.RevoAndroidDebug, 'backendVersion', {
        configurable: true,
        enumerable: true,
        get: () => VERSION,
        set: () => {}
      });
    } catch (_) {
      window.RevoAndroidDebug.backendVersion = VERSION;
    }
    window.RevoAndroidDebug.patternCatalogVersion = VERSION;
    window.RevoAndroidDebug.availablePatterns = () => {
      const list = availablePatternList();
      return list ? currentNames(list).slice() : [];
    };
  }

  function install() {
    if (!runtime()) {
      setTimeout(install, 25);
      return;
    }
    if (window.__revoAndroidV0210PatternsInstalled) return;
    window.__revoAndroidV0210PatternsInstalled = true;

    const attempt = (label) => {
      pinDebugVersion();
      return repairAvailablePatterns(label);
    };

    // The Android preload batch does not write state.config.availablePatterns,
    // so it is safe to seed as soon as dataRuntime exists. Repeat after the
    // existing delayed backend repairs in case another startup path recreates it.
    attempt('runtime-ready');
    setTimeout(() => attempt('postload-250ms'), 250);
    setTimeout(() => attempt('postload-1s'), 1000);
    setTimeout(() => attempt('postload-3.5s'), 3500);
    setTimeout(() => attempt('postload-5.5s'), 5500);
    setTimeout(pinDebugVersion, 6000);

    console.log('[android-backend] v0.2.10 Gather pattern catalog repair installed');
  }

  install();
})();

// Revolution Android backend overlay v0.2.12 lifecycle bridge.
// Keeps the desktop Start/Pause/Stop control state synchronized with the native
// Android macro engine and fail-closes duplicate lifecycle taps while a native
// transition is still settling.
(() => {
  const VERSION = '0.2.12-lifecycle.1';
  const POLL_MS = 200;
  const START_GRACE_MS = 5000;
  const TRANSITION_TIMEOUT_MS = 10000;

  let transition = null; // 'starting' | 'stopping' | 'pausing' | null
  let transitionSince = 0;
  let transitionAccount = 'Default';
  let transitionSerial = 0;
  let installed = false;

  const now = () => Date.now();

  function runtime() {
    return window.dataRuntime || null;
  }

  function macroApi() {
    return window.go && window.go.cmd && window.go.cmd.Macro
      ? window.go.cmd.Macro
      : null;
  }

  function accountName(account) {
    const text = String(account ?? '').trim();
    if (text) return text;
    const rt = runtime();
    return String((rt && rt.account) || 'Default');
  }

  function readEngineState() {
    try {
      if (!window.AndroidRevo || typeof AndroidRevo.getEngineState !== 'function') return null;
      const raw = AndroidRevo.getEngineState();
      return typeof raw === 'string' ? JSON.parse(raw || '{}') : (raw || {});
    } catch (e) {
      console.error('[android-lifecycle] getEngineState failed', String(e));
      return null;
    }
  }

  function macroState(account) {
    const rt = runtime();
    if (!rt || typeof rt.stateObject !== 'function') return null;
    try { return rt.stateObject(accountName(account)); }
    catch (e) {
      console.error('[android-lifecycle] stateObject failed', String(e));
      return null;
    }
  }

  function setRuntimeState(account, running, paused, status) {
    const target = accountName(account);
    const state = macroState(target);
    if (!state) return false;
    const emit = window.runtime && typeof window.runtime.EventsEmit === 'function'
      ? window.runtime.EventsEmit.bind(window.runtime)
      : null;
    if (!emit) return false;

    // Publish native lifecycle state as backend-originated Revo events. This is
    // important: using Object.Set() here would create synthetic *_client ACKs and
    // schedule configuration persistence on every poll. Backend 'set' events
    // update the reactive keyed state.macros list without that write churn.
    const desired = {
      running: !!running,
      paused: !!paused,
      status: String(status || (running ? 'Running' : 'Stopped'))
    };
    for (const [field, value] of Object.entries(desired)) {
      if (typeof state.Concrete === 'function' && state.Concrete(field) === value) continue;
      emit('set', `state.macros[${target}].${field}`, -1, value);
    }
    return true;
  }

  function optimisticStatus(kind) {
    if (kind === 'starting') return 'Starting';
    if (kind === 'stopping') return 'Stopping';
    if (kind === 'pausing') return 'Pausing';
    return '';
  }

  function beginTransition(kind, account) {
    transition = kind;
    transitionSince = now();
    transitionAccount = accountName(account);
    transitionSerial += 1;
    return transitionSerial;
  }

  function clearTransition(expectedSerial) {
    if (expectedSerial !== undefined && expectedSerial !== transitionSerial) return false;
    transition = null;
    transitionSince = 0;
    return true;
  }

  function syncFromEngine(reason = 'poll') {
    const state = readEngineState();
    if (!state) return null;
    const account = transition ? transitionAccount : accountName();
    const age = transition ? now() - transitionSince : 0;
    const nativeRunning = state.running === true;
    const nativePaused = state.paused === true;
    const nativeStatus = String(state.status || (nativeRunning ? 'Running' : 'Stopped'));

    if (transition === 'starting') {
      if (nativeRunning) {
        clearTransition();
        setRuntimeState(account, true, nativePaused, nativeStatus);
      } else if (age < START_GRACE_MS) {
        // Native startup can include launching/switching to Roblox. Keep Start
        // locked during that window so a second tap cannot stack another launch.
        setRuntimeState(account, true, false, optimisticStatus('starting'));
      } else {
        clearTransition();
        setRuntimeState(account, false, false, nativeStatus);
      }
      return state;
    }

    if (transition === 'stopping') {
      if (!nativeRunning) {
        clearTransition();
        setRuntimeState(account, false, false, nativeStatus);
      } else if (age < TRANSITION_TIMEOUT_MS) {
        // Keep Start disabled until native confirms it actually stopped.
        setRuntimeState(account, true, nativePaused, optimisticStatus('stopping'));
      } else {
        clearTransition();
        setRuntimeState(account, true, nativePaused, nativeStatus);
      }
      return state;
    }

    if (transition === 'pausing') {
      if (nativePaused || !nativeRunning || age >= TRANSITION_TIMEOUT_MS) clearTransition();
      setRuntimeState(account, nativeRunning, nativePaused, nativeStatus);
      return state;
    }

    setRuntimeState(account, nativeRunning, nativePaused, nativeStatus);
    return state;
  }

  function install() {
    const rt = runtime();
    const macro = macroApi();
    if (!rt || !macro || !window.runtime || typeof window.runtime.EventsEmit !== 'function' ||
        !window.AndroidRevo || typeof AndroidRevo.getEngineState !== 'function') {
      setTimeout(install, 25);
      return;
    }
    if (installed || macro.__revoAndroidV0212LifecycleInstalled) return;
    installed = true;

    const originalStart = macro.Start;
    const originalPause = macro.Pause;
    const originalStop = macro.Stop;
    const originalStopAll = macro.StopAll;

    macro.Start = async (account) => {
      const target = accountName(account);
      const current = readEngineState();
      if (transition || (current && current.running === true && current.paused !== true)) {
        syncFromEngine('duplicate-start');
        console.warn('[android-lifecycle] ignored duplicate Start while active/transitioning');
        return null;
      }

      const serial = beginTransition('starting', target);
      setRuntimeState(target, true, false, optimisticStatus('starting'));
      try {
        return await originalStart(target);
      } catch (e) {
        clearTransition(serial);
        syncFromEngine('start-error');
        throw e;
      }
    };

    macro.Pause = async (account) => {
      const target = accountName(account);
      const current = readEngineState();
      if (transition || !current || current.running !== true || current.paused === true) {
        syncFromEngine('ignored-pause');
        return null;
      }
      const serial = beginTransition('pausing', target);
      try {
        return await originalPause(target);
      } catch (e) {
        clearTransition(serial);
        syncFromEngine('pause-error');
        throw e;
      }
    };

    macro.Stop = async (account) => {
      const target = accountName(account);
      const current = readEngineState();
      if (transition === 'stopping') {
        syncFromEngine('duplicate-stop');
        return null;
      }
      // A Stop during the startup grace window is intentionally allowed so the
      // user can cancel after one Start tap even before native reports running.
      if (transition !== 'starting' && (!current || current.running !== true)) {
        syncFromEngine('ignored-stop');
        return null;
      }

      const serial = beginTransition('stopping', target);
      setRuntimeState(target, true, false, optimisticStatus('stopping'));
      try {
        return await originalStop(target);
      } catch (e) {
        clearTransition(serial);
        syncFromEngine('stop-error');
        throw e;
      }
    };

    macro.StopAll = async () => {
      const target = accountName();
      const current = readEngineState();
      if (transition === 'stopping') return null;
      if (transition !== 'starting' && (!current || current.running !== true)) {
        syncFromEngine('ignored-stop-all');
        return null;
      }
      const serial = beginTransition('stopping', target);
      setRuntimeState(target, true, false, optimisticStatus('stopping'));
      try {
        return await originalStopAll();
      } catch (e) {
        clearTransition(serial);
        syncFromEngine('stop-all-error');
        throw e;
      }
    };

    macro.__revoAndroidV0212LifecycleInstalled = true;
    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.lifecycleVersion = VERSION;
    window.RevoAndroidDebug.lifecycle = () => ({
      transition,
      transitionSince,
      transitionAccount,
      transitionSerial,
      engine: readEngineState()
    });
    window.RevoAndroidDebug.syncLifecycle = () => syncFromEngine('debug');

    syncFromEngine('install');
    const poll = () => {
      try { syncFromEngine('poll'); }
      catch (e) { console.error('[android-lifecycle] poll failed', String(e)); }
      setTimeout(poll, POLL_MS);
    };
    setTimeout(poll, POLL_MS);
    console.log('[android-backend] v0.2.12 lifecycle bridge installed');
  }

  install();
})();
