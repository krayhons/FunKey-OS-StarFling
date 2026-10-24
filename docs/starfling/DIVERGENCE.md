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
| Boot time | `rcS` starts S12, S13, S20 and S40–S42 3 s late in the background | Off the boot path (Phase 1.3) | Phase 1.3 |
| Boot time | Audio setup in `starfling-audio-init`, started from `inittab`: amp warm-up with `tinyplay` (`/usr/share/starfling/silence-10ms.wav`), then S50alsa-utils' restore, then the saved volume (moved from `/root/.profile`). `rcS` no longer starts S50alsa-utils; `frontend` and `instant_play` wait for the warm-up (`starfling-audio-wait`) | The codec driver's 700 ms amp power-up sleep and the mixer work that waits on it leave the critical path (Phase 1.3) | Phase 1.3 |
| Boot time | RetroFE patch `0023-wait-for-audio-warmup.patch` (wait for the warm-up flag before `Mix_OpenAudio`, not before starting RetroFE); `rcS` starts S02–S04 late and S49/S52 in parallel; `swapon` in the background; `.profile` creates directories only when missing | Fast path to the frontend (Phase 1.3) | Phase 1.3 |
| Boot time | picoarch patch `0002-wait-for-audio-warmup.patch`: wait for the warm-up flag where audio is opened; `instant_play` skips its own wait for picoarch | A resumed game's core and content loading overlap the amp warm-up (Phase 1.3) | Phase 1.3 |
| Boot time | RetroFE patch `0021-lazy-quick-menu.patch`: the quick menu (13 fonts incl. the CJK fallback, images, zones) is set up on first MENU press, not at startup or on each return from a game | ~0.2 s on the menu boot path (Phase 1.2 baseline) | Phase 1.4 |
| Boot time | `share init` sets up the USB gadget in the background 3 s later (nice 19), creates share directories only when missing, and `usb_gadget` computes the serial/MAC only when building a gadget | USB gadget and adb's `sleep 5` off the boot path | Phase 1.3 |
