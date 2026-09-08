// Revolution Android backend overlay v0.2.5
// Implements preset/account configuration operations against Revo's own dataRuntime.
(() => {
  const DEFAULT_PRESET_KEY = 'revo.android.defaultPreset.v1';

  const rt = () => window.dataRuntime;
  const cloneValue = (v) => {
    if (v === undefined) return '';
    try { return JSON.parse(JSON.stringify(v)); }
    catch (_) { return String(v ?? ''); }
  };

  function presetList() {
    const runtime = rt();
    // This also ensures settings.presets is initialized as a keyed list with keyField=name.
    runtime.presetObject('Default');
    return runtime.Object('settings').List('presets');
  }

  function presetEntry(name) {
    const key = String(name ?? '').trim();
    if (!key) return null;
    const list = presetList();
    return (list.values || []).find((x) => x && x.key === key) || null;
  }

  function presetExists(name) {
    return !!presetEntry(name);
  }

  function clearList(list) {
    if (!list || !Array.isArray(list.values)) return;
    while (list.values.length) {
      const key = list.keyField ? list.values[0].key : 0;
      list.Delete(key);
    }
  }

  function cloneObject(src, dst, skipValues = new Set()) {
    if (!src || !dst) return;
    const vals = src.values && typeof src.values === 'object' && !Array.isArray(src.values) ? src.values : {};
    for (const [name, rec] of Object.entries(vals)) {
      if (skipValues.has(name) || !rec || !Object.prototype.hasOwnProperty.call(rec, 'value')) continue;
      dst.Set(name, cloneValue(rec.value));
    }
    const objects = src.objects && typeof src.objects === 'object' ? src.objects : {};
    for (const [name, child] of Object.entries(objects)) {
      if (!child || typeof child !== 'object') continue;
      if (Array.isArray(child.values)) cloneList(child, dst.List(name));
      else cloneObject(child, dst.Object(name));
    }
  }

  function cloneList(src, dst) {
    if (!src || !dst) return;
    clearList(dst);
    const srcValues = Array.isArray(src.values) ? src.values : [];
    const keyField = String(src.keyField ?? '');
    const primitive = !!src.primitive;
    dst.keyField = keyField;
    dst.primitive = primitive;

    if (keyField) {
      for (const item of srcValues) {
        if (!item || !item.key || !item.object) continue;
        const created = dst.Append(String(item.key));
        cloneObject(item.object, created, new Set([keyField]));
      }
      return;
    }
    if (primitive) {
      for (const item of srcValues) dst.Append('', cloneValue(item));
      return;
    }
    for (const item of srcValues) {
      const created = dst.Append('');
      cloneObject(item, created);
    }
  }

  function validPresetName(name) {
    const n = String(name ?? '').trim();
    if (!n) return { error: 'Preset name cannot be empty.' };
    if (n.includes('[') || n.includes(']')) return { error: 'Preset name cannot contain [ or ].' };
    return { name: n };
  }

  async function createPreset(name) {
    const v = validPresetName(name);
    if (v.error) return v.error;
    if (presetExists(v.name)) return `Preset "${v.name}" already exists`;
    presetList().Append(v.name);
    return null;
  }

  async function duplicatePreset(sourceName, newName) {
    const srcName = String(sourceName ?? '').trim();
    const v = validPresetName(newName);
    if (v.error) return v.error;
    const src = presetEntry(srcName);
    if (!src) return `Preset "${srcName}" does not exist`;
    if (presetExists(v.name)) return `Preset "${v.name}" already exists`;
    const dst = presetList().Append(v.name);
    cloneObject(src.object, dst, new Set(['name']));
    return null;
  }

  function accountObjects() {
    const root = rt().Object('accounts');
    return root && root.objects && typeof root.objects === 'object' ? root.objects : {};
  }

  async function setAccountPreset(accountName, presetName) {
    const account = String(accountName ?? 'Default').trim() || 'Default';
    const preset = String(presetName ?? 'Default').trim() || 'Default';
    if (!presetExists(preset)) return `Preset "${preset}" does not exist`;
    if (account === 'Default') {
      try { localStorage.setItem(DEFAULT_PRESET_KEY, preset); } catch (_) {}
      rt().Object('state').Set('defaultPreset', preset);
    } else {
      rt().Object('accounts').Object(account).Set('preset', preset);
    }
    return null;
  }

  async function renamePreset(oldName, newName) {
    const oldKey = String(oldName ?? '').trim();
    const v = validPresetName(newName);
    if (v.error) return v.error;
    if (oldKey === v.name) return null;
    const src = presetEntry(oldKey);
    if (!src) return `Preset "${oldKey}" does not exist`;
    if (presetExists(v.name)) return `Preset "${v.name}" already exists`;

    const dst = presetList().Append(v.name);
    cloneObject(src.object, dst, new Set(['name']));

    const runtime = rt();
    if ((runtime.defaultPreset || 'Default') === oldKey) {
      await setAccountPreset('Default', v.name);
    }
    for (const [account, obj] of Object.entries(accountObjects())) {
      if (obj && obj.Concrete && obj.Concrete('preset') === oldKey) obj.Set('preset', v.name);
    }

    if (runtime.preset === oldKey) runtime.setPreset(v.name);
    presetList().Delete(oldKey);
    return null;
  }

  async function deletePreset(name) {
    const key = String(name ?? '').trim();
    const list = presetList();
    const entry = presetEntry(key);
    if (!entry) return `Preset "${key}" does not exist`;
    if ((list.values || []).length <= 1) return 'Cannot delete the only preset.';

    const remaining = (list.values || []).filter((x) => x && x.key !== key);
    const fallback = (remaining.find((x) => x.key === 'Default') || remaining[0]).key;
    const runtime = rt();

    if ((runtime.defaultPreset || 'Default') === key) await setAccountPreset('Default', fallback);
    for (const [account, obj] of Object.entries(accountObjects())) {
      if (obj && obj.Concrete && obj.Concrete('preset') === key) obj.Set('preset', fallback);
    }
    if (runtime.preset === key) runtime.setPreset(fallback);
    list.Delete(key);
    return null;
  }

  async function resetSettings() {
    try { AndroidRevo.stopAll(); } catch (_) {}
    try {
      localStorage.removeItem('revo.android.runtime.snapshot.v1');
      localStorage.removeItem(DEFAULT_PRESET_KEY);
      localStorage.removeItem('revo.color');
    } catch (_) {}
    setTimeout(() => location.reload(), 40);
    return null;
  }

  function install() {
    if (!window.go || !window.go.cmd || !window.go.cmd.Macro || !window.dataRuntime) {
      setTimeout(install, 25);
      return;
    }
    const macro = window.go.cmd.Macro;
    macro.CreatePreset = createPreset;
    macro.DeletePreset = deletePreset;
    macro.DuplicatePreset = duplicatePreset;
    macro.RenamePreset = renamePreset;
    macro.SetAccountPreset = setAccountPreset;
    macro.ResetSettings = resetSettings;

    // v0.2.4 persists settings/accounts, but defaultPreset is a critical state value.
    // Restore it from a tiny dedicated per-Android-user key after preload is ready.
    const restoreDefaultPreset = () => {
      try {
        const saved = localStorage.getItem(DEFAULT_PRESET_KEY);
        if (saved && presetExists(saved)) rt().Object('state').Set('defaultPreset', saved);
      } catch (e) {
        console.error('[android-backend] default preset restore failed', e);
      }
    };
    setTimeout(restoreDefaultPreset, 150);

    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.backendVersion = '0.2.5';
    window.RevoAndroidDebug.listPresets = () => (presetList().values || []).map((x) => x.key);
    console.log('[android-backend] v0.2.5 preset/account backend installed');
  }

  install();
})();
