# Divergence from upstream

Every intentional difference between StarFling and its base,
[L-K-M/FunKey-OS-Starling](https://github.com/L-K-M/FunKey-OS-Starling)
(Starling 3.1.3), is listed here, so the delta stays readable. One row per
change; link the PR.

| Area | Change | Why | PR |
|---|---|---|---|
| Branding | Name, version scheme (`StarFling-X.Y.Z`, restarting at 0.1.0), repo URLs. The `FunKey-` artifact prefix is kept | New fork identity; the prefix is globbed by installed firmware (D7) | Phase 0 |
| CI | Z.ai/GLM review workflow removed (archived in `docs/archive/starling/`) | Not used by StarFling | Phase 0 |
| Boot timing | `etc/init.d/rcS` replaces Buildroot's copy (same loop plus one boot mark per script); boot marks in `.profile`, `frontend` and `instant_play`; new `/usr/local/lib/bootmark`, `bootmark`, `starfling-boot-collect`. All inert unless `/mnt/starfling-boot/` exists | Phase 1 boot-time measurement (task 1.1) | Phase 1.1 |
| Boot timing | RetroFE patch `0020-starfling-boot-marks.patch` | Same; RetroFE startup steps on the kernel clock | Phase 1.1 |
| Boot timing | BusyBox `CONFIG_BOOTCHARTD` and `CONFIG_FEATURE_SEAMLESS_GZ` on | Optional bootchart; its `tar -z` needs seamless gzip | Phase 1.1 |
| Scripts | `ro` exits 1 with a message when the read-only remount fails, and 0 when `/` is already read-only (upstream: always 0, or 1 when already read-only) | A failed remount looked like success and left `/` writable before power-off | Phase 1.1 |
