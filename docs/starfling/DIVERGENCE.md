# Divergence from upstream

Every intentional difference between StarFling and its base,
[L-K-M/FunKey-OS-Starling](https://github.com/L-K-M/FunKey-OS-Starling)
(Starling 3.1.3), is listed here, so the delta stays readable. One row per
change; link the PR.

| Area | Change | Why | PR |
|---|---|---|---|
| Branding | Name, version scheme (`StarFling-X.Y.Z`, restarting at 0.1.0), repo URLs. The `FunKey-` artifact prefix is kept | New fork identity; the prefix is globbed by installed firmware (D7) | Phase 0 |
| CI | Z.ai/GLM review workflow removed (archived in `docs/archive/starling/`) | Not used by StarFling | Phase 0 |
| Boot time | `share init` sets up the USB gadget in the background 3 s later (nice 19), creates share directories only when missing, and `usb_gadget` computes the serial/MAC only when building a gadget | USB gadget and adb's `sleep 5` off the boot path | Phase 1.3 |
