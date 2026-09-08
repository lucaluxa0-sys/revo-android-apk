(async () => {
  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  await sleep(500);
  try {
    const rt = window.dataRuntime;
    if (!rt) throw new Error('missing dataRuntime');

    const safeConcrete = (obj, key) => {
      try {
        if (!obj || typeof obj.Concrete !== 'function') return null;
        const value = obj.Concrete(key);
        return value === undefined ? null : value;
      } catch (error) {
        return `ERR:${String(error)}`;
      }
    };

    const state = rt.Object('state');
    const config = state.Object('config');
    const available = config.List('availablePatterns');
    const rawAvailable = Array.isArray(available.values) ? available.values : [];

    const preset = rt.Preset();
    const active = preset.Object('patterns').List('active');
    const rawActive = Array.isArray(active.values) ? active.values : [];
    const configKeys = [
      'gatherPattern', 'seconds', 'backpackPercent', 'walkReturn',
      'invertFB', 'invertLR', 'shiftLock', 'zoom', 'length', 'width',
      'distance', 'alignment', 'repetitions', 'driftComp', 'position',
      'yaw', 'pitch'
    ];

    const output = {
      backend: window.RevoAndroidDebug && window.RevoAndroidDebug.backendVersion,
      runtimeDisconnected: !!rt.disconnected,
      presetName: rt.preset || rt.defaultPreset || '',
      availablePatterns: {
        primitive: !!available.primitive,
        keyField: String(available.keyField || ''),
        count: rawAvailable.length,
        values: rawAvailable.slice(0, 80).map(value => {
          if (value === null || value === undefined) return value;
          if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
          return {
            type: value.constructor && value.constructor.name || typeof value,
            name: safeConcrete(value, 'name'),
            id: safeConcrete(value, 'id')
          };
        })
      },
      activeMeta: {
        primitive: !!active.primitive,
        keyField: String(active.keyField || ''),
        count: rawActive.length
      },
      active: []
    };

    for (let index = 0; index < Math.min(rawActive.length, 20); index++) {
      const row = rawActive[index];
      if (!row) continue;
      const item = {
        index,
        field: safeConcrete(row, 'field'),
        order: safeConcrete(row, 'order'),
        id: safeConcrete(row, 'id'),
        config: {}
      };
      try {
        const fieldConfig = row.Object('config');
        for (const key of configKeys) item.config[key] = safeConcrete(fieldConfig, key);
      } catch (error) {
        item.configError = String(error);
      }
      output.active.push(item);
    }

    console.error('RevoV029GatherState ' + JSON.stringify(output));
    return output;
  } catch (error) {
    console.error('RevoV029GatherState ERROR ' + String(error) + ' ' + (error && error.stack || ''));
    throw error;
  }
})();
