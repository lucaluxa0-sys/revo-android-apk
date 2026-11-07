# Revo REA: traceable movement-plan research

This is an **isolated, incomplete** compatibility implementation built from
the user's recovered Revolution Macro evidence. It does not replace a working
desktop macro, bypass any account/licensing mechanism, or send game input itself.

## What runs today

- `planner/` compiles a bounded subset of genuine Revolution-style Lua commands
  into a deterministic JSON action plan, including loops and `Pattern` expressions.
- `scripts/e_lol.lua` restores the evidenced 18-step `e_lol` gather geometry
  already present in the Android adapter (width 2, length 8).
- `cmd/revo-plan` is a Windows/Linux CLI that **only generates plans**.
- `android-sandbox/RevoActionPlan.java` validates one movement-only plan;
  reject on unsupported operations, malformed metadata or duration mismatch.
- `tools/patch_android_plan_intake.py` prepares an isolated Android
  `RevoGatherAdapter` allowing validated plans when the caller explicitly sets
  `enablePlannedExecution:true`. The old hardcoded `e_lol` remains as fallback.
- Native gesture dispatch still uses the existing app's display-scoped
  accessibility engine and Roblox-foreground check. No gesture is fired in tests.

## Execute the compiler locally

```sh
cd research/revo-plan
go test ./...
go run ./cmd/revo-plan -script scripts/e_lol.lua -width 2 -length 8 -out e_lol.json
```

Output schema: `revo.action-plan.v1`. It includes the source SHA-256,
movement timing calibration, pattern name, and an ordered action list.
The planner marks output `dryRunOnly:true`: generating a plan does not
authorize a device to execute it. The Android adapter separately requires
`enablePlannedExecution:true`, intentionally absent by default.

## Supported and unsupported

Compiler accepts `SetName`, `Walk`, `Sleep`, `SleepStuds`, `KeyDown`,
`KeyUp`, and `SetYaw`; generic Lua loops/expressions can generate commands.
The **Android** adapter currently accepts only cardinal `walk` commands.
Detector, alignment, parachute, checkpoint, camera, PvE, and timed-table
commands fail closed. It is not accurate to call these features ported.

The compiler has no OS, IO, package, dynamic file-loader or Roblox hooks.
Execution is bounded by action count, finite geometry and a deadline.
The native loader checks plan schema, source hash syntax, exact selected
pattern, finite distances, gesture duration, calibration and allowed actions.

## Verification

- Go unit tests check recovered route geometry, width scaling, loop timeout,
  movement calibration, invalid distances and unsupported commands.
- The host Java tests compile the actual plan validator against `org.json`
  and exercise the adapter configuration path using no-input Android stubs.
- A separate CI research gate must compile the patched Android application
  before treating this work as build-ready. The actual phone has NOT been tested.

## Scope, provenance and licensing

Historical reference source at `third_party/revolution-2025-gpl` is covered by
its included GPLv3 license. That older source is **not proof** of the current
signed `RevolutionMacro.exe` implementation. Keep copyright and licensing
notices when reusing any GPL code. The 2026 REA analysis of the current binary
is kept locally; this research directory does not publish extracted executable
assets, private account data, or entitlement information.

The current binary's recovered frontend references 62 Wails methods.
The previously inspected Android shim exposes all 62 names, but 34 of the
46 macro methods were classified as no-op placeholders; API presence alone
is not functional parity. Do not ship as a complete Revo clone.
