// Revolution Android backend overlay v0.2.8.2
// Finalizes this interaction patch set and prevents older asynchronous overlays
// from overwriting the diagnostic backend version after installation.
(() => {
  const VERSION = '0.2.8.2';

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
    console.log('[android-backend] v0.2.8.2 final overlay installed');
  }

  function install() {
    if (!window.dataRuntime || !window.go || !window.go.cmd || !window.go.cmd.Macro) {
      setTimeout(install, 25);
      return;
    }
    pinVersion();
    // Reassert after slower installers have had a chance to complete.
    setTimeout(pinVersion, 500);
    setTimeout(pinVersion, 1500);
  }

  install();
})();
