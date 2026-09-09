# Revolution Android Port — Active Execution State

This file is the durable handoff/checkpoint for long ChatGPT engineering sessions on `lucaluxa0-sys/revo-android-apk`.

## Continuity rule

GitHub is the persistent execution state. Chat is only the temporary working session.

For every future continuation of this project:

1. Re-fetch live `main` before making any repository write. Do not trust a SHA copied from chat.
2. Read this file before resuming work.
3. Treat committed code and GitHub Actions evidence as authoritative over chat summaries.
4. Commit every meaningful implementation/fix before waiting on a long CI run.
5. Before a response is likely to end, or before a long external wait, update this file with the exact blocker and next action. Use `[skip ci]` for state-only commits so checkpoints do not waste Android CI.
6. After a failed CI run: fetch the exact run/job logs and artifacts, patch the concrete failure, commit, and rerun. Do not stop merely to report status.
7. Do not weaken emulator assertions just to make CI green.
8. Avoid repetitive status chatter while CI is running. Spend the execution window on repository work, diagnostics, commits, and evidence.
9. If a ChatGPT execution window ends unexpectedly, the next session resumes from this file plus live `main`; no large conversational recovery should be required.
10. This file is for the Revolution Android port only. Do not touch the separate Qwen apprenticeship project when following it.

## Current objective

Make the v0.2.9 Android gather engine gate pass on the real Android 15 / API 35 Pixel 6 emulator, then integrate the proven engine slice into the shipping APK workflow.

The required proof remains the real path:

`screenshot/frame capture -> MacroEngine.onFrame() -> recovered Revolution e_lol pattern -> display-scoped Android accessibility gestures`

Do not substitute a fake timer/tap demo for the recovered Revolution movement behavior.

## Current live repository state at checkpoint creation

- Live `main` observed immediately before this state file was created: `ffc7a91bd3734064b28e22b0c5a31d18b121f6c2`
- That SHA is a GitHub Actions bot publish commit for the dev APK.
- Its parent containing the latest engine/UI-driver work is: `17a17669b5e96007453f71cad3f85297ed2ffe3a`
- Latest engine helper hardening commit: `17a17669b5e96007453f71cad3f85297ed2ffe3a` — `Harden Android 15 accessibility UI activation probe`

Always re-fetch live `main` before acting because CI may publish another commit after this checkpoint.

## Current engine gate

Workflow:

- `.github/workflows/test-v029-engine-adapter.yml`
- Name: `Test v0.2.9 gather engine adapter`

Latest completed engine run at checkpoint creation:

- Run ID: `34382981214`
- Job ID: `102572140037`
- Result: **failure**
- APK build: **passed**
- Instrumentation/source verification: **passed**
- Android 15 emulator step `Boot Android 15 and execute recovered e_lol adapter`: **failed**
- Evidence upload step: **passed**

## What has already been proven

- The v0.2.9 Android engine source compiles.
- Real per-display screenshot/frame capture plumbing exists.
- Real display-scoped accessibility input plumbing exists (`tap` / `swipe` / joystick-style dispatch).
- The recovered desktop `e_lol` adapter is wired into the v0.2.9 engine probe.
- The Android Accessibility service manifest/declaration is valid and requests gesture + screenshot capabilities.
- `ACCESS_RESTRICTED_SETTINGS` can be placed in `allow` in the Android 15 emulator; that is no longer the primary blocker.
- Direct writes to `enabled_accessibility_services` were rejected/cleared by Android 15 and must not be used as fake proof.
- CI was changed to exercise the real Android Settings UI path for enabling Revolution Accessibility.
- The first Settings UI driver failed because legacy `uiautomator dump` returned `null root node`.
- The current helper now wakes/unlocks the emulator, attempts a direct Accessibility service-detail deep link, retries hierarchy capture, and records focus/window diagnostics plus screenshots on failure.

## Current blocker

Run `34382981214` still failed in the Android 15 emulator after the hardened Settings-UI activation helper was added.

The final run-9 evidence/logs have **not yet been fully inspected**. Do not guess the next Android behavior from earlier runs.

## Exact next action

1. Re-fetch live `main`.
2. Fetch run `34382981214`, job `102572140037`, and its uploaded engine evidence artifact.
3. Inspect the new Accessibility Settings focus/window diagnostics, hierarchy retries, screenshots, and logcat from run 9.
4. Identify the exact screen/activity or activation failure shown by that evidence.
5. Patch `.ci/enable_revo_accessibility.py` or the Android service activation flow based on that evidence.
6. Commit the fix.
7. Follow the new Android 15 run through the emulator step.
8. Once Accessibility binds, keep the existing strict engine assertions and continue until the real `e_lol` frame-to-gesture path is proven.
9. After that, move directly into the next real engine slice / shipping integration rather than returning to UI-only polish.

## Shipping status

The broader v0.2.8.1 UI/runtime/Auto-Planters work was previously emulator-verified, but the Android macro engine is **not complete**. Do not tell the user the Samsung-ready Revolution macro is finished until real engine behavior is proven in emulator and then on-device-relevant flow.

## Working style for this repo

When the user says `continue`, `keep working`, or similar, begin GitHub/CI operations immediately. Do not answer with only a plan or status message.
