# Revolution Macro Android — developer APK

Public download repository for the Revo Android + multi-session developer build.

## Latest download

[Download RevolutionMacro-Android-v0.2.10-Samsung-Test.apk](https://raw.githubusercontent.com/lucaluxa0-sys/revo-android-apk/main/RevolutionMacro-Android-v0.2.10-Samsung-Test.apk)

SHA-256:

`711d1e7bbac26bbc253fed119d38307abce684ac1ac982df5a2017a5b8e00cb2`

Build provenance: [BUILD_PROVENANCE-v0210-samsung-test.txt](BUILD_PROVENANCE-v0210-samsung-test.txt)

v0.2.10 fixes the Android Gather pattern selector by restoring the real Revolution pattern catalog into `state.config.availablePatterns`. The Android 15 / API 35 Pixel 6 emulator regression gate cold-started the app, opened the real Gather row and Pattern control, and verified all 15 recovered pattern options are visible, including `e_lol`, `CornerXSnake`, and `BambooAlt`.

Selector evidence: [GitHub Actions run 34411501626](https://github.com/lucaluxa0-sys/revo-android-apk/actions/runs/34411501626)

This build still contains the real desktop frontend, Android runtime compatibility, recovered assets, native capture/input plumbing, and the narrow recovered Gather execution adapter. The full desktop Revolution decision/routine engine is still under active recovery and is not complete.

Older developer APKs remain in this repository for reference.
