// Revolution Android backend overlay v0.2.8.1
// Repairs the keyed-list metadata that desktop Revo normally receives during preload.
(() => {
  const VERSION = '0.2.8.1';

  function runtime() { return window.dataRuntime; }

  function currentPreset() {
    const r = runtime();
    if (!r || typeof r.presetObject !== 'function') return null;
    return r.presetObject(r.preset || r.defaultPreset || 'Default');
  }

  function listIsValidKeyed(list, keyField) {
    if (!list || !Array.isArray(list.values)) return false;
    if (list.keyField !== keyField) return false;
    return list.values.every(item => item && typeof item === 'object' && item.object && String(item.key || '') !== '');
  }

  function clearMalformedList(list) {
    if (!list || !Array.isArray(list.values)) return;
    // Delete by numeric index while it is still an unkeyed list. This also keeps
    // dataRuntime's reactive subscribers and persistence path in sync.
    while (list.values.length) {
      try { list.Delete(0); }
      catch (_) { list.values.splice(0, 1); }
    }
  }

  function repairKeyedList(list, keyField) {
    if (!list) return false;

    const values = Array.isArray(list.values) ? list.values : [];
    const malformed = values.some(item => !item || typeof item !== 'object' || !item.object || String(item.key || '') === '');

    // Old Android builds allowed Revo to append these lists before keyField was
    // known. Those entries are unusable Qr objects (no {key, object} wrapper),
    // and Revo later crashes at item.object.Concrete(...). Remove only that
    // malformed representation, then restore the desktop schema.
    if (malformed || (values.length && list.keyField && list.keyField !== keyField)) {
      clearMalformedList(list);
    }

    list.keyField = keyField;
    list.primitive = false;
    try { list.Flush(); } catch (_) {}
    return listIsValidKeyed(list, keyField);
  }

  function pinVersion() {
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
  }

  function repairAutoPlantersSchema() {
    const preset = currentPreset();
    if (!preset) return false;

    const auto = preset.Object('planter').Object('autoPlanters');
    const okNectars = repairKeyedList(auto.List('nectars'), 'type');
    const okFields = repairKeyedList(auto.List('fields'), 'field');
    const okPlanters = repairKeyedList(auto.List('planters'), 'planter');

    // Defaults used by the Settings tab. Value() has UI fallbacks, but writing
    // them here makes the runtime shape match desktop Revo and persist cleanly.
    const defaults = {
      enabled: false,
      harvestAfterHours: 24,
      harvestMinHours: 0,
      harvestFullyGrown: true,
      harvestAutomatically: false,
      buildNectars: 2,
      maintainNectars: 1,
      baselineNectarHours: 0,
      degradationMultiplier: 1,
      maxPlanters: 3
    };
    for (const [key, value] of Object.entries(defaults)) {
      if (auto.Concrete(key) === undefined) auto.Set(key, value);
    }

    const r = runtime();
    if (r && r.Object('planters').Concrete('introShowed') === undefined) {
      r.Object('planters').Set('introShowed', false);
    }

    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.autoPlanterSchema = () => ({
      nectars: { keyField: auto.List('nectars').keyField, count: auto.List('nectars').values.length },
      fields: { keyField: auto.List('fields').keyField, count: auto.List('fields').values.length },
      planters: { keyField: auto.List('planters').keyField, count: auto.List('planters').values.length }
    });
    pinVersion();

    console.log('[android-backend] v0.2.8.1 Auto-Planters keyed schema ready', okNectars, okFields, okPlanters);
    return true;
  }

  function install() {
    if (!window.dataRuntime || !window.go || !window.go.cmd || !window.go.cmd.Macro) {
      setTimeout(install, 25);
      return;
    }
    if (!repairAutoPlantersSchema()) {
      setTimeout(install, 50);
      return;
    }
    // v0.2.5/v0.2.6 installers can finish later depending on WebView timing.
    // Keep this overlay authoritative after they have settled.
    setTimeout(pinVersion, 250);
    setTimeout(pinVersion, 1000);
    setTimeout(pinVersion, 2500);
  }

  install();
})();
