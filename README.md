# Revolution Macro Android — developer APK

Public download repository for the Revo Android + multi-session developer build.

## Latest download

[Download RevolutionMacro-Android-v0.2.11-Samsung-Test.apk](https://raw.githubusercontent.com/lucaluxa0-sys/revo-android-apk/main/RevolutionMacro-Android-v0.2.11-Samsung-Test.apk)

SHA-256:

`e2acbb3ad45e0dafaf00817c11680c182903a82506ffb3ef227f36eb8b617242`

Build provenance: [BUILD_PROVENANCE-v0211-samsung-test.txt](BUILD_PROVENANCE-v0211-samsung-test.txt)

v0.2.11 fixes the Android Start handoff that previously opened generic Roblox and stopped there. Start now launches Bee Swarm Simulator directly with `roblox://placeId=1537690962`, and the native macro engine starts only after that launch request succeeds.

The Android 15 / API 35 Pixel 6 end-to-end gate exercised the real Revolution Start button with an active `e_lol` Gather row, enabled the real Revolution Accessibility service, verified the Bee Swarm Roblox URI, ran the recovered 18-step `e_lol` adapter, injected foreground movement, and required Revolution's visual movement detector to confirm a visible response.

End-to-end evidence: [GitHub Actions run 34416809503](https://github.com/lucaluxa0-sys/revo-android-apk/actions/runs/34416809503)

v0.2.10's Gather selector repair remains included, so the real Pattern control still exposes the recovered Revolution pattern catalog. `e_lol` is currently the pattern with the narrow recovered native execution adapter. The full desktop Revolution decision/routine engine and generic execution for the other recovered Gather patterns are still under active recovery and are not complete.

Older developer APKs remain in this repository for reference.
