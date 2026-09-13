# Physical Samsung remote test setup

This document configures the narrow v0.2.12 physical-phone regression channel. It does **not** expose a shell, package installer, filesystem API, or arbitrary command execution. The phone agent listens on TCP port `38421` and supports only `ping`, `pair`, `status`, `start`, `stop`, and the bounded `sunflower-e2e` command.

Do not put a Tailscale auth key, Revo pairing code, or Revo bearer token in this repository, an issue, a workflow log, or chat.

## 1. Install and open the current phone preview

Install the current v0.2.12 phone-preview APK that contains `RevoRemoteAgent`, then open Revolution on the Samsung.

If the app is not paired yet, it shows an Android toast like:

`Revo remote pairing code: 123456 (10 min)`

The six-digit value is temporary and expires after 10 minutes. If the code expires before pairing, fully close/restart the app so an unpaired agent can create a fresh pairing window.

The pairing code is **not** the long-term token.

## 2. Find the Samsung's private Tailscale address

On the Samsung's Tailscale app, obtain either:

- the phone's Tailscale `100.x.x.x` address, or
- its private MagicDNS hostname.

Use that private address as `REVO_PHONE_HOST`. Do not use a public Internet address and do not forward port `38421` through the router.

The GitHub Actions runner must be allowed by the tailnet's access policy to reach the Samsung on TCP port `38421`.

## 3. Pair once from a trusted machine

From a trusted machine that can already reach the Samsung over Tailscale, run the repository client with the temporary six-digit code:

```bash
python3 tools/revo-phone-agent-client.py --host <tailscale-phone-host> pair <six-digit-code>
```

On success, the client stores the random bearer token in:

`~/.revo-phone-agent-token`

with restrictive local permissions where supported. Keep this token secret. Do not paste it into source control.

You can verify the paired agent without controlling the macro:

```bash
python3 tools/revo-phone-agent-client.py --host <tailscale-phone-host> ping
python3 tools/revo-phone-agent-client.py --host <tailscale-phone-host> status
```

`ping` does not require the bearer token. `status` does.

## 4. Create the GitHub Actions Tailscale credential

The current workflows use `tailscale/github-action@v4` with an auth key stored only as a GitHub Actions secret.

Tailscale's current GitHub Action guidance recommends that an auth key used by CI have a tag identity and be reusable and ephemeral. If device approval is enabled, it should also be pre-approved. See Tailscale's official GitHub Action documentation:

https://tailscale.com/docs/integrations/github/github-action

Create the key in Tailscale's admin console and keep the key value private.

## 5. Add the three repository settings

In GitHub open:

`Settings -> Secrets and variables -> Actions`

Create the following **repository variable**:

- `REVO_PHONE_HOST` = the Samsung's private Tailscale IP or MagicDNS hostname

Create the following **repository secrets**:

- `TAILSCALE_AUTHKEY` = the tagged/reusable/ephemeral Tailscale auth key for the CI runner
- `REVO_PHONE_TOKEN` = the bearer token created by the Revo `pair` command

Do not use the six-digit pairing code as `REVO_PHONE_TOKEN`.

## 6. Run the read-only gate first

Before any physical movement test, run the workflow:

`Probe physical Samsung read only`

This workflow performs only:

1. configuration-presence validation,
2. private Tailscale join,
3. unauthenticated `ping`,
4. authenticated `status`.

It does **not** call `start`, `stop`, or `sunflower-e2e`.

A valid current phone preview must return authoritative fields including:

- `engineKnown: true`
- boolean `engineRunning`
- boolean `enginePaused`
- string `transition`

If those fields are missing or malformed, stop. That normally means an older APK is installed or the native bridge is not ready.

## 7. Movement stays gated behind authoritative state

Only after the read-only gate succeeds should `Physical Samsung remote control` be used.

For `start` and `sunflower-e2e`, the workflow first checks authoritative engine state and refuses unsafe/ambiguous starts. After a control command, it samples engine state again and fails unless the requested state actually took effect.

The bounded Sunflower physical route remains a test-only path; a successful HTTP response by itself is not proof of gameplay parity.

## Recovery notes

- If `ping` fails, fix Tailscale reachability/ACLs before touching macro controls.
- If `ping` succeeds but `status` returns `401`, the GitHub `REVO_PHONE_TOKEN` does not match the paired token stored by the app.
- If pairing reports `already_paired`, do not keep guessing codes. Use the existing token or intentionally clear/reinstall the app only if you mean to re-pair.
- If `engineKnown` is false, do not send Start/Sunflower. Open the current preview and let its Android/native bridge initialize.
- The Samsung must be awake/unlocked with Roblox in the correct foreground state before a gameplay movement test. The remote test channel does not bypass Android lockscreen, consent, or account boundaries.
