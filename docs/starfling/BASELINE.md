# StarFling boot baseline (Phase 1 task 1.2)

**Status: draft.** The timing round (10 menu + 10 game boots, adb off, phone
video) has not run yet. Everything below comes from boots with adb on
(which adds a fixed ~5.5 s in S10share, excluded here) and from experiments
run live over adb on 2026-10-23. Numbers marked *(prelim.)* will be replaced
by medians from K's round; the confirmed experiments stand on their own.

Build: StarFling 0.1.0 + task 1.1 instrumentation (`.fwu` `757848ea…`,
PR #3), Kodak 64 GB reference card, theme RetroRoomCovers, `firstCollection
= Main`.

## Method

- On-device: boot marks in the kernel log (init scripts, `.profile`,
  RetroFE), collected per boot into `/mnt/starfling-boot/NNN/`; optional
  bootchart. See `PHASE-1-BOOT.md` 1.1 and `DEVLOOP.md` section 7.
- Wall clock: K's 240 fps video, `docs/starfling/boot-timing-template.csv`.
- Pre-kernel time (BROM, SPL, U-Boot, kernel decompression) = video time to
  the first menu frame − kernel time at RetroFE's `menu first frame` mark.
- Report: `tools/starfling/boot-report.py <folder> --video <csv>`.

## Results from the timing round

*(Pending K's round. Fill in: median power-on → menu drawn, → menu
responds, → game moving; pre-kernel median; per-stage medians.)*

| Measure (median of 10) | Menu path | Game path |
|---|---|---|
| Power-on → menu drawn / game moving (video) | | |
| Power-on → menu responds (video) | | — |
| Pre-kernel (video − kernel clock) | | (menu value) |
| Kernel clock → menu accepts input | | — |

## Stage breakdown, menu path *(prelim., boot 002, adb on)*

Times on the kernel clock; S10share's adb `sleep 5` excluded.

| Stage | From → to | ms | Notes |
|---|---|---:|---|
| Pre-kernel | power-on → kernel clock 0 | ? | From video only |
| Kernel | clock 0 → init | 573 | fbtft panel init ~146, USB host EHCI/OHCI ~100, pinctrl/serial ~76 |
| sysinit | init → rcS start | 208 | `mount -a` (FAT) ~115, `swapon` ~53, syslogd/klogd, ~12 forked commands |
| rcS without S10share | rcS start → rcS end | ~370 | S50alsa-utils 113, S02sysctl 41, S01first_boot 38, S20urandom 35 |
| S10share without adb | | ? | Normal-boot cost unknown until the round |
| Login + `.profile` | rcS end → frontend exec | 287 | `.profile` start → volume/brightness restored 182 (`volume set` alone ~120) |
| RetroFE exec → `main` | | 338 | Cold page-in of 22 libraries (~10 MB); 52 ms warm |
| Config import | `main` → config imported | 171 | 58 ms warm |
| SDL init | → sdl initialized | 874 | ~750 is the audio amplifier power-up sleep (confirmed below) |
| GStreamer init | → video initialized | 241 | Video is disabled (`videoEnable = no`) and unused by every layout |
| Splash, init thread, layout, fonts, collection, menu build | → menu first frame | ~380 | Fonts ~90 |
| Menu onEnter animation | first frame → accepts input | 268 | Theme-dependent |
| **Kernel clock → menu accepts input** | | **~3.7 s + S10share** | |

## Confirmed by experiment (2026-10-23, live over adb)

1. **The audio codec's amplifier power-up costs ~0.75 s on RetroFE's main
   thread.** The V3s analog codec driver
   (`sound/soc/sunxi/sun8i-codec-analog.c`, `sun8i_headphone_amp_event`)
   does `msleep(700)` whenever the headphone/speaker amp powers up, which
   happens when a playback stream starts and the amp has been off for more
   than about 5 s. `Mix_OpenAudio` in `SDL::initialize` hits it.
   - `aplay` of 0.1 s silence: 0.89 to 0.93 s cold, 0.15 s warm.
   - RetroFE `config imported → sdl initialized`: 848 / 897 ms cold vs
     121 / 121 ms when a 10 ms `aplay` warmed the amp just before.
   - The game path pays it too. picoarch + gpsp with Anguna, PCM open →
     running: 770 / 780 ms with a cold amp, 40 / 20 ms warm (exec → open
     ~210 ms in all runs). Whether the first gameplay frame waits for it is
     for the round's video to show; picoarch sets up audio during its
     platform init, before the core runs.
2. **RetroFE's early startup is SD-card bound, not CPU bound.** exec →
   `main` 338 ms cold vs 52 ms warm; config import 171 vs 58 ms. Reading the
   binary plus its 12 largest libraries end to end takes 0.18 s cold, so
   demand paging costs about twice a sequential read. Raw card reads about
   21 MB/s (`dd`, 1 MiB blocks).
3. **Bootchart (boot 003)**: the CPU is saturated from rcS end to the menu
   except for two idle windows: the adb `sleep 5` and ~0.6 s inside RetroFE
   SDL init (finding 1). iowait peaks (50–72 %) at RetroFE exec.

4. **Userspace commands, timed live (warm cache, so lower bounds for
   boot):** `volume set` 120 ms (`bc`, three `amixer` calls, `audio_amp on`,
   and a U-Boot env write when the value changes); `volume get` 30;
   `brightness get`/`set` 20 each; `assembly_tests` 20; `alsactl restore`
   40 (113 at boot, cold); `S02sysctl` 40; `S20urandom` 20;
   `S13system-stats` 20; `keymap default` 30; `instant_play load` with no
   game 20; `fw_printenv` 10; `hwclock` 10. A bare fork+exec is ~4.5 ms.

## Top time sinks *(prelim.)*

| # | Sink | Est. ms (menu) | Path(s) |
|---|---|---:|---|
| 1 | Audio amp power-up sleep (kernel `msleep(700)` on first playback) | 750 | menu, game (both measured) |
| 2 | Kernel init (fbtft, USB host, probe) | 573 | both |
| 3 | RetroFE splash → menu build (layout, fonts, collection) | ~380 | menu |
| 4 | RetroFE exec, cold library page-in | 338 | menu |
| 5 | Login + `.profile` (volume/brightness via scripts, `mkdir -p`) | 287 | both |
| 6 | Menu onEnter animation before input | 268 | menu |
| 7 | GStreamer pre-init with video disabled | 241 | menu |
| 8 | sysinit (`mount -a`, `swapon`, forks) | 208 | both |
| 9 | Config import (cold reads) | 171 | menu |
| 10 | `alsactl restore` (S50alsa-utils) | 113 | both |
| — | Pre-kernel, S10share without adb | ? | both; from the round |

## Levers, re-ranked *(prelim.)*

| Lever | Task | Est. saving | Confidence |
|---|---|---:|---|
| Warm the amp in the background early in boot (a short silent stream right after the codec probes), or open audio off RetroFE's main thread; never shorten the kernel sleep without listening for pops | 1.3 / 1.5a | ~0.75 s menu and game | High (measured on both) |
| Skip `VideoFactory::createVideo()` when `videoEnable = no`; then drop GStreamer linkage | 1.4 | 0.24 s + part of exec page-in | High (measured cost) |
| Userspace fast path: frontend straight from init, defer late services (`alsactl`, sysctl, urandom, system-stats), fewer forks in `.profile` | 1.3 | 0.4–0.7 s | Medium |
| Prefetch RetroFE and its libraries in the background during kernel/sysinit idle time, or trim libraries | 1.3 / 1.4 | 0.1–0.2 s | Medium |
| Shorter or no onEnter animation for the first menu | 1.4 | up to 0.27 s | Medium (theme) |
| Kernel trim: USB host off the boot path (1.5a), fbtft init, logo | 1.5 | 0.1–0.3 s | Medium |
| Pre-kernel (U-Boot) | 1.6 | ? | After the round |

## Other observations

- Every boot logs `FAT-fs (mmcblk0p4): Volume was not properly unmounted`,
  including after a clean `reboot`. No fsck runs, so it costs no time, but
  it means the share partition's dirty bit is never cleared on shutdown.
  Added to the Phase 1 backlog (`PHASE-1-BOOT.md`) for data safety;
  Instant Play saves live there.
- RetroFE's `rememberMenu` is in-memory only: a cold boot always opens
  `firstCollection` (Main). The brief's "restoring Favorites triggers a full
  scan" does not apply at boot.
- Leaving Recovery hung once more (`plan.md` task 0.5): 2 failures in about
  9 exits.
