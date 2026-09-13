# v0.2.12 clean-startup UI evidence — 2026-09-13

## Purpose

Investigate the reported Android startup condition where a control appeared to be already selected/on, without guessing at an unidentified `Follow` setting.

The diagnostic intentionally performs **no macro control**. It does not enable the Revolution Accessibility service, press Start, launch Roblox, or call the remote-control agent.

## Frozen APK under test

- Product commit: `fcf55c1cc3cc86e0e499a7d170b4b8b6d13e3cb9`
- APK: `RevolutionMacro-Android-v0.2.12-PHONE-PREVIEW-fcf55c1.apk`
- APK SHA-256: `3081041fda623c1cdcdd3e34d8c2f058ed504abb3123df6588a2a5a9439bfbf7`
- Original build run: `34726199539`

The diagnostic downloaded the original GitHub Actions artifact from that build and verified the APK SHA-256 before launching it. No reconstructed APK was substituted.

## Runtime environment and procedure

Diagnostic workflow:

`.github/workflows/diag-v0212-clean-startup-ui.yml`

Successful run:

`34728162072`

Evidence artifact:

- Artifact ID: `10308596925`
- Name: `revo-v0212-clean-startup-ui-34728162072`
- Artifact digest: `sha256:a9afc7ae062d68f1e2a80ed4e49b15da9e9e35779f18287b6b19c19eaf42275e`

Runtime:

- Android 15 / API 35
- Google APIs x86_64
- Pixel 6 emulator profile
- app data cleared with `pm clear com.revolution.android` before launch
- Revolution launched directly as `com.revolution.android/.MainActivity`
- no Accessibility-service enable by the workflow
- no Start press
- no Roblox install/launch by the workflow
- no remote-control endpoint call

Untouched screenshots and UIAutomator hierarchies were captured around 8, 20, and 35 seconds after launch.

## Findings

The clean startup does **not** reproduce a user-facing option being silently turned on.

At the settled 20-second and 35-second captures:

- the screenshots are byte-identical (`SHA-256 18503a89c1ef913a431be2e16cdf6e11df5f1abac3d70ae0967c7291d8936ad1`), so the UI is stable rather than changing itself later;
- macro status is `Stopped`;
- Start is enabled;
- Pause is disabled;
- Stop is disabled;
- Preset is `Default`;
- Account is `Disabled`;
- there are **zero** UIAutomator nodes with `checked="true"`;
- the only node with `selected="true"` is the expected top-level `Gather` tab;
- `Collect`, `Planters`, `Status`, `Tools`, and `Settings` are not selected;
- no `Follow` text or accessibility description exists anywhere in the captured hierarchy.

The 8-second screenshot is still on Revolution's native startup splash (`Starting Revolution Macro...`), while later captures show the settled frontend.

## Source/bundle cross-check

The exact APK's web assets were searched case-insensitively for `follow`.

Only unrelated occurrences were found:

1. explanatory text stating that planter clock mode *follows* current time;
2. two third-party selector-library strings in the Mantine bundle.

There is no Revolution user-facing control/state literal named `Follow` in the exact APK bundle.

The Android bootstrap regression separately enforces that startup `baseOps` may inject only internal bootstrap state, with `state.ready` as the only `true` boolean. Persisted user configuration is replayed separately from bootstrap defaults.

## Conclusion

The hypothesis that the v0.2.12 Android bootstrap itself enables a `Follow`-like user setting on a clean install is rejected by runtime evidence.

The remaining plausible explanations for the physical-phone report are:

1. a previously persisted Revolution setting/state in the Android WebView/app data;
2. a device-specific rendering/label interpretation on the Samsung;
3. a control other than the one described as `Follow`.

Do **not** patch or reset an unidentified setting based on the report alone. Preserve user configuration until the physical control is identified by a screenshot or grounded state evidence.

The physical Samsung read-only network gate remains separately blocked until `REVO_PHONE_HOST` and `TAILSCALE_AUTHKEY` are configured in GitHub Actions; authenticated status additionally requires the paired `REVO_PHONE_TOKEN`.
