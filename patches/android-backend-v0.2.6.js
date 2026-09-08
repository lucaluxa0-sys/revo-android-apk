// Revolution Android backend overlay v0.2.6
// Adds real Gather pattern copy/paste operations on top of v0.2.5.
(() => {
  const CLIPBOARD_KEY = 'revo.android.patternClipboard.v1';

  const rt = () => window.dataRuntime;
  const cloneValue = (v) => {
    if (v === undefined) return '';
    try { return JSON.parse(JSON.stringify(v)); }
    catch (_) { return String(v ?? ''); }
  };

  function currentPreset() {
    const runtime = rt();
    if (!runtime || typeof runtime.presetObject !== 'function') return null;
    return runtime.presetObject(runtime.preset || runtime.defaultPreset || 'Default');
  }

  function ensureKey(list, keyField) {
    if (!list) return null;
    if (!list.keyField) list.keyField = String(keyField || '');
    if (list.primitive === undefined) list.primitive = false;
    return list;
  }

  function patternLists() {
    const preset = currentPreset();
    if (!preset) return null;
    const patterns = preset.Object('patterns');
    return {
      active: ensureKey(patterns.List('active'), 'id'),
      defaults: ensureKey(patterns.List('defaults'), 'field')
    };
  }

  function findPattern(id, isDefault) {
    const lists = patternLists();
    if (!lists) return null;
    const key = String(id ?? '').trim();
    if (!key) return null;

    if (isDefault) {
      const direct = lists.defaults.Object(key);
      if (direct) return { entry: direct, list: lists.defaults, key, isDefault: true };
      const active = lists.active.Object(key);
      const field = active && active.Concrete ? String(active.Concrete('field') || '') : '';
      if (field) {
        const byField = lists.defaults.Object(field);
        if (byField) return { entry: byField, list: lists.defaults, key: field, isDefault: true };
      }
    } else {
      const direct = lists.active.Object(key);
      if (direct) return { entry: direct, list: lists.active, key, isDefault: false };
      const byField = lists.defaults.Object(key);
      if (byField) return { entry: byField, list: lists.defaults, key, isDefault: true };
    }
    return null;
  }

  function snapshotObject(obj) {
    if (!obj || typeof obj !== 'object') return { values: {}, objects: {} };
    const values = {};
    const objects = {};
    const rawValues = obj.values && typeof obj.values === 'object' && !Array.isArray(obj.values) ? obj.values : {};
    for (const [name, rec] of Object.entries(rawValues)) {
      if (!rec || !Object.prototype.hasOwnProperty.call(rec, 'value')) continue;
      values[name] = cloneValue(rec.value);
    }
    const rawObjects = obj.objects && typeof obj.objects === 'object' ? obj.objects : {};
    for (const [name, child] of Object.entries(rawObjects)) {
      if (!child || typeof child !== 'object') continue;
      if (Array.isArray(child.values)) objects[name] = snapshotList(child);
      else objects[name] = { kind: 'object', data: snapshotObject(child) };
    }
    return { values, objects };
  }

  function snapshotList(list) {
    const keyField = String(list.keyField ?? '');
    const primitive = !!list.primitive;
    const items = [];
    for (const item of Array.isArray(list.values) ? list.values : []) {
      if (keyField) {
        if (!item || !item.key || !item.object) continue;
        items.push({ key: String(item.key), data: snapshotObject(item.object) });
      } else if (primitive) {
        items.push(cloneValue(item));
      } else {
        items.push(snapshotObject(item));
      }
    }
    return { kind: 'list', keyField, primitive, items };
  }

  function clearList(list) {
    if (!list || !Array.isArray(list.values)) return;
    while (list.values.length) {
      const key = list.keyField ? list.values[0].key : 0;
      list.Delete(key);
    }
  }

  function applyObjectSnapshot(dst, snap) {
    if (!dst || !snap) return;
    for (const [name, value] of Object.entries(snap.values || {})) dst.Set(name, cloneValue(value));
    for (const [name, child] of Object.entries(snap.objects || {})) {
      if (!child || typeof child !== 'object') continue;
      if (child.kind === 'list') applyListSnapshot(dst.List(name), child);
      else applyObjectSnapshot(dst.Object(name), child.data || child);
    }
  }

  function applyListSnapshot(dst, snap) {
    if (!dst || !snap) return;
    clearList(dst);
    dst.keyField = String(snap.keyField || '');
    dst.primitive = !!snap.primitive;
    for (const item of Array.isArray(snap.items) ? snap.items : []) {
      if (dst.keyField) {
        const created = dst.Append(String(item.key));
        applyObjectSnapshot(created, item.data);
      } else if (dst.primitive) {
        dst.Append('', cloneValue(item));
      } else {
        const created = dst.Append('');
        applyObjectSnapshot(created, item);
      }
    }
  }

  function setClipboard(payload) {
    window.__revoAndroidPatternClipboard = payload;
    try { localStorage.setItem(CLIPBOARD_KEY, JSON.stringify(payload)); } catch (_) {}
  }

  function getClipboard() {
    if (window.__revoAndroidPatternClipboard) return window.__revoAndroidPatternClipboard;
    try {
      const raw = localStorage.getItem(CLIPBOARD_KEY);
      if (raw) return JSON.parse(raw);
    } catch (_) {}
    return null;
  }

  async function copyPattern(id, isDefault) {
    const src = findPattern(id, !!isDefault);
    if (!src) {
      console.warn('[android-backend] CopyPattern target not found', id, isDefault);
      return 'Pattern not found';
    }
    const field = src.entry.Concrete ? String(src.entry.Concrete('field') || src.key) : src.key;
    setClipboard({
      version: 1,
      sourceKey: src.key,
      field,
      config: snapshotObject(src.entry.Object('config'))
    });
    console.log(`[android-backend] copied pattern ${field || src.key}`);
    return null;
  }

  async function loadPattern(id, isDefault) {
    const dst = findPattern(id, !!isDefault);
    if (!dst) {
      console.warn('[android-backend] LoadPattern target not found', id, isDefault);
      return 'Pattern not found';
    }
    const payload = getClipboard();
    if (!payload || !payload.config) return 'No copied pattern available';
    applyObjectSnapshot(dst.entry.Object('config'), payload.config);
    const field = dst.entry.Concrete ? String(dst.entry.Concrete('field') || dst.key) : dst.key;
    console.log(`[android-backend] pasted pattern ${payload.field || payload.sourceKey} -> ${field || dst.key}`);
    return null;
  }

  function install() {
    if (!window.go || !window.go.cmd || !window.go.cmd.Macro || !window.dataRuntime) {
      setTimeout(install, 25);
      return;
    }
    const macro = window.go.cmd.Macro;
    macro.CopyPattern = copyPattern;
    macro.LoadPattern = loadPattern;

    window.RevoAndroidDebug = window.RevoAndroidDebug || {};
    window.RevoAndroidDebug.backendVersion = '0.2.6';
    window.RevoAndroidDebug.patternClipboard = () => getClipboard();
    console.log('[android-backend] v0.2.6 gather pattern backend installed');
  }

  install();
})();
