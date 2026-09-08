// Android Wails compatibility runtime for Revolution Macro frontend.
// v0.2.4: ACK Revo dataRuntime client mutations and persist user configuration per Android user/WebView profile.
(() => {
  const listeners = new Map();
  const PERSIST_KEY = 'revo.android.runtime.snapshot.v1';
  const PERSIST_ROOTS = ['settings', 'planters', 'accounts'];
  let persistTimer = 0;

  function onMultiple(name, callback, maxCallbacks) {
    const key = String(name);
    const rec = { callback, remaining: Number(maxCallbacks) };
    if (!listeners.has(key)) listeners.set(key, []);
    listeners.get(key).push(rec);
    return () => {
      const arr = listeners.get(key) || [];
      const next = arr.filter(x => x !== rec);
      if (next.length) listeners.set(key, next); else listeners.delete(key);
    };
  }

  function off(...names) {
    for (const name of names) listeners.delete(String(name));
  }

  function emit(name, ...args) {
    const key = String(name);
    const arr = [...(listeners.get(key) || [])];
    for (const rec of arr) {
      try { rec.callback(...args); }
      catch (e) { console.error('[android-runtime] listener failed', key, e); }
      if (Number.isFinite(rec.remaining) && rec.remaining > 0) {
        rec.remaining -= 1;
        if (rec.remaining === 0) {
          const current = listeners.get(key) || [];
          const next = current.filter(x => x !== rec);
          if (next.length) listeners.set(key, next); else listeners.delete(key);
        }
      }
    }
  }

  function jsonSafeValue(value) {
    if (value === undefined) return '';
    try { return JSON.parse(JSON.stringify(value)); }
    catch (_) { return String(value ?? ''); }
  }

  function serializeObject(obj, out) {
    if (!obj || typeof obj !== 'object') return;
    const base = String(obj.path ?? '');
    const vals = obj.values && typeof obj.values === 'object' && !Array.isArray(obj.values) ? obj.values : {};
    for (const [name, rec] of Object.entries(vals)) {
      if (!rec || !Object.prototype.hasOwnProperty.call(rec, 'value')) continue;
      out.push({ op: 'set', path: `${base}.${name}`, value: jsonSafeValue(rec.value) });
    }
    const objects = obj.objects && typeof obj.objects === 'object' ? obj.objects : {};
    for (const child of Object.values(objects)) {
      if (!child || typeof child !== 'object') continue;
      if (Array.isArray(child.values)) serializeList(child, out);
      else serializeObject(child, out);
    }
  }

  function serializeList(list, out) {
    if (!list || typeof list !== 'object') return;
    const base = String(list.path ?? '');
    const primitive = !!list.primitive;
    const keyField = String(list.keyField ?? '');

    // Recreate the list's type before replaying its members.
    out.push({ op: 'append', path: `${base}[_init]`, primitive, key: keyField });

    const values = Array.isArray(list.values) ? list.values : [];
    for (let index = 0; index < values.length; index += 1) {
      const item = values[index];
      if (keyField) {
        const key = item && typeof item === 'object' ? String(item.key ?? '') : '';
        if (!key) continue;
        out.push({ op: 'append', path: `${base}[${key}]`, primitive: false, key: keyField });
        if (item.object) serializeObject(item.object, out);
      } else if (primitive) {
        out.push({ op: 'append', path: `${base}[${index}]`, value: jsonSafeValue(item), primitive: true, key: '' });
      } else {
        out.push({ op: 'append', path: `${base}[${index}]`, primitive: false, key: '' });
        serializeObject(item, out);
      }
    }
  }

  function snapshotPersistentRuntime() {
    const rt = window.dataRuntime;
    if (!rt || !rt.roots) return [];
    const ops = [];
    for (const rootName of PERSIST_ROOTS) serializeObject(rt.roots[rootName], ops);
    return ops;
  }

  function persistNow() {
    persistTimer = 0;
    try {
      const ops = snapshotPersistentRuntime();
      localStorage.setItem(PERSIST_KEY, JSON.stringify({ version: 1, ops }));
      console.log(`[android-runtime] persisted runtime ops=${ops.length}`);
    } catch (e) {
      console.error('[android-runtime] persist failed', e);
    }
  }

  function queuePersist() {
    if (persistTimer) clearTimeout(persistTimer);
    persistTimer = setTimeout(persistNow, 80);
  }

  function loadPersistedOps() {
    try {
      const raw = localStorage.getItem(PERSIST_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      const ops = parsed && parsed.version === 1 && Array.isArray(parsed.ops) ? parsed.ops : [];
      console.log(`[android-runtime] loaded persisted runtime ops=${ops.length}`);
      return ops;
    } catch (e) {
      console.error('[android-runtime] persisted runtime load failed', e);
      return [];
    }
  }

  // Revo dataRuntime optimistically applies mutations, then waits up to five seconds
  // for the backend to echo the event id. Wails normally provides that echo. Without
  // it, dataRuntime marks the backend disconnected and the UI greys out.
  function ackClientMutation(name, args) {
    try {
      if (name === 'set_client') {
        const [path, value, id] = args;
        emit('set', String(path), Number(id), value);
        queuePersist();
        return true;
      }
      if (name === 'append_client') {
        const [path, _value, id] = args;
        // For an ACK, dataRuntime only needs a matching id; it returns before applying payload fields.
        emit('append', String(path), Number(id), false, '');
        queuePersist();
        return true;
      }
      if (name === 'delete_client') {
        const [path, id] = args;
        emit('delete', String(path), Number(id));
        queuePersist();
        return true;
      }
    } catch (e) {
      console.error('[android-runtime] mutation ACK failed', name, e);
    }
    return false;
  }

  function eventsEmit(name, ...args) {
    const key = String(name);
    // Preserve normal local event delivery first, then emulate the Wails backend ACK.
    emit(key, ...args);
    ackClientMutation(key, args);
  }

  window.runtime = {
    EventsOnMultiple: onMultiple,
    EventsOff: (...names) => off(...names),
    EventsEmit: (name, ...args) => eventsEmit(name, ...args),
    BrowserOpenURL: (url) => { try { console.log('[android-runtime] BrowserOpenURL', url); } catch (_) {} },
    Hide: () => null,
    Show: () => null,
    ClipboardGetText: async () => ''
  };

  // Compatibility alias for code that probes Wails-style host objects.
  window.wails = {
    EventsNotify: (payload) => {
      try {
        const evt = typeof payload === 'string' ? JSON.parse(payload) : payload;
        if (evt && evt.name) emit(evt.name, ...(Array.isArray(evt.data) ? evt.data : []));
      } catch (e) {
        console.error('[android-runtime] EventsNotify failed', e);
      }
    }
  };

  window.chrome = window.chrome || {};
  window.chrome.webview = window.chrome.webview || { postMessage: () => {} };

  const noop = async () => null;
  const macro = {
    AckPreload: noop, AddDefaultField: noop, BanIdentity: noop, ConnectRelay: noop,
    CopyLogsFile: noop, CopyPattern: noop, CreatePreset: noop, DeleteField: noop,
    DeletePreset: noop, DisconnectRelay: noop, DuplicatePreset: noop,
    ExportPresetToClipboard: noop, ExportPresetToFile: noop,
    GetBackgroundImageData: async () => null,
    GetColorScheme: async () => localStorage.getItem('revo.color') || 'blue',
    GetFontServerBaseURL: async () => '', GetOSVersion: async () => 'Android',
    GetSystemFonts: async () => [], HopEmptyServer: noop, HopFullServer: noop,
    ImportPreset: noop, ImportPresetSelectFile: noop, LoadPattern: async () => null,
    MoveAlt: noop, MoveTadAlt: noop, NotifyUIBoot: noop, OpenLogsFolder: noop,
    Pause: async (a) => AndroidRevo.pauseMacro(String(a ?? 'Default')),
    RecordHotkey: async () => '', RefreshPlanterSchedule: noop, RefreshServers: noop,
    RegenerateOnionAddress: noop, RemoveBackgroundImage: noop, RenamePreset: noop,
    ResetAlt: noop,
    ResetSettings: async () => {
      try { localStorage.removeItem(PERSIST_KEY); } catch (_) {}
      return null;
    },
    SelectBackgroundImage: noop, SetAccountPreset: noop,
    SetColorScheme: async (v) => { localStorage.setItem('revo.color', String(v)); return null; },
    SetPatternDefault: noop, SetTheme: noop,
    Start: async (a) => AndroidRevo.startMacroAndRoblox(String(a ?? 'Default')),
    StartRelay: noop,
    Stop: async (a) => AndroidRevo.stopMacro(String(a ?? 'Default')),
    StopAll: async () => AndroidRevo.stopAll(), StopRelay: noop
  };
  const analytics = {
    GetMyAccounts: async () => ({accounts: []}), SetCurrentAccount: noop, UpsertMacroAccount: noop
  };
  const auth = {
    Bind: noop, CancelAuthFlow: noop, GetUser: async () => null, IsSupporter: async () => false,
    Logout: noop, StartAuthFlow: noop, UserHasOnePrivilege: async () => false,
    ValidateSession: async () => false
  };
  const fflags = {
    Get: async () => '', GetBool: async () => false, GetBoolUser: async () => false,
    GetUser: async () => '', List: async () => []
  };
  window.go = { cmd: { Macro: macro, AnalyticsHandler: analytics, AuthHandler: auth, FFlagsHandler: fflags } };
  window.RevoAndroidDebug = {
    state: () => JSON.parse(AndroidRevo.getEngineState()),
    displayId: () => AndroidRevo.getDisplayId(),
    listeners: () => [...listeners.keys()],
    persistedOps: () => loadPersistedOps(),
    persistNow: () => persistNow(),
    clearPersistence: () => localStorage.removeItem(PERSIST_KEY)
  };

  const boot = () => {
    if (!window.runtime || !window.dataRuntime) {
      setTimeout(boot, 25);
      return;
    }
    console.log('[android-runtime] frontend runtime ready; sending preload');
    const baseOps = [
      {op:'set', path:'state.ready', value:true},
      {op:'set', path:'state.activeAccount', value:'Default'},
      {op:'set', path:'state.defaultPreset', value:'Default'},
      {op:'set', path:'auth.sessionId', value:''},
      {op:'set', path:'auth.hwid', value:'android'}
    ];
    const ops = [...loadPersistedOps(), ...baseOps];
    emit('preload_batch', ops);
    // Let the preload batch flush before releasing the startup overlay.
    setTimeout(() => emit('startup:done'), 50);
  };

  window.addEventListener('DOMContentLoaded', () => setTimeout(boot, 0));
})();
