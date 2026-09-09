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
