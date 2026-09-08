// Android Wails compatibility runtime for Revolution Macro frontend.
(() => {
  const listeners = new Map();

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

  window.runtime = {
    EventsOnMultiple: onMultiple,
    EventsOff: (...names) => off(...names),
    EventsEmit: (name, ...args) => emit(name, ...args),
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
    ResetAlt: noop, ResetSettings: noop, SelectBackgroundImage: noop,
    SetAccountPreset: noop,
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
    listeners: () => [...listeners.keys()]
  };

  const boot = () => {
    if (!window.runtime || !window.dataRuntime) {
      setTimeout(boot, 25);
      return;
    }
    console.log('[android-runtime] frontend runtime ready; sending preload');
    const ops = [
      {op:'set', path:'state.ready', value:true},
      {op:'set', path:'state.activeAccount', value:'Default'},
      {op:'set', path:'state.defaultPreset', value:'Default'},
      {op:'set', path:'auth.sessionId', value:''},
      {op:'set', path:'auth.hwid', value:'android'}
    ];
    emit('preload_batch', ops);
    // Let the preload batch flush before releasing the startup overlay.
    setTimeout(() => emit('startup:done'), 50);
  };

  window.addEventListener('DOMContentLoaded', () => setTimeout(boot, 0));
})();
