// Revolution Android backend overlay v0.2.9
// Configures the first desktop-grounded Android gather routine before Start.
(() => {
  const VERSION = '0.2.9';
  const rt = () => window.dataRuntime;

  function currentPreset() {
    const r = rt();
    if (!r || typeof r.presetObject !== 'function') return null;
    return r.presetObject(r.preset || r.defaultPreset || 'Default');
  }

  function number(v, fallback) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  }

  function localNumber(key, fallback) {
    try { return number(localStorage.getItem(key), fallback); } catch (_) { return fallback; }
  }

  function selectedGatherEntry() {
    const preset = currentPreset();
    if (!preset) return null;
    const list = preset.Object('patterns').List('active');
    const entries = (list.values || []).filter(x => x && x.object);
    entries.sort((a, b) => number(a.object.Concrete('order'), 0) - number(b.object.Concrete('order'), 0));
    return entries[0] || null;
  }

  function buildEngineConfig(account) {
    const preset = currentPreset();
    const entry = selectedGatherEntry();
    if (!preset || !entry) {
      return { routine: 'gather', account: String(account || 'Default'), patternName: '', requireRobloxForeground: true };
    }
    const c = entry.object.Object('config');
    const patternName = String(c.Concrete('gatherPattern') || '');
    const macro = preset.Object('macro');
    return {
      routine: 'gather',
      account: String(account || 'Default'),
      field: String(entry.object.Concrete('field') || ''),
      patternName,
      width: number(c.Concrete('width'), 2),
      length: number(c.Concrete('length'), 8),
      repetitions: number(c.Concrete('repetitions'), 0),
      alignment: number(c.Concrete('alignment'), 0),
      keyDelayMs: number(macro.Concrete('keyDelay'), 50),
      // Desktop Lua geometry is exact. These mobile timing/joystick values are
      // intentionally exposed because physical Roblox calibration is still pending.
      msPerStud: localNumber('revo.android.msPerStud', 62.5),
      joystickCenterX: localNumber('revo.android.joystickCenterX', 0.16),
      joystickCenterY: localNumber('revo.android.joystickCenterY', 0.78),
      joystickRadius: localNumber('revo.android.joystickRadius', 0.085),
      requireRobloxForeground: true
    };
  }

  function pinVersion() {
    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    try {
      Object.defineProperty(window.RevoAndroidDebug, 'backendVersion', {
        configurable: true, enumerable: true, get: () => VERSION, set: () => {}
      });
    } catch (_) { window.RevoAndroidDebug.backendVersion = VERSION; }
  }

  function install() {
    if (!window.go || !window.go.cmd || !window.go.cmd.Macro || !window.dataRuntime ||
        !window.AndroidRevo || typeof AndroidRevo.configureMacro !== 'function') {
      setTimeout(install, 25); return;
    }
    const m = window.go.cmd.Macro;
    if (m.__revoAndroidV029Installed) return;
    const originalStart = m.Start;
    m.Start = async (account) => {
      const cfg = buildEngineConfig(account);
      try {
        const state = JSON.parse(AndroidRevo.configureMacro(JSON.stringify(cfg)) || '{}');
        console.log('[android-engine] configured', JSON.stringify(cfg), JSON.stringify(state));
      } catch (e) {
        console.error('[android-engine] configure failed', String(e));
      }
      return originalStart(account);
    };
    m.__revoAndroidV029Installed = true;
    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.engineConfig = (account='Default') => buildEngineConfig(account);
    pinVersion();
    // v0.2.8.1 pins its version after delayed preload repairs; stay authoritative.
    setTimeout(pinVersion, 3000);
    setTimeout(pinVersion, 5000);
    console.log('[android-backend] v0.2.9 gather engine bridge installed');
  }

  install();
})();
