# StarFling boot baseline (Phase 1 task 1.2)

**Status: final for 1.2.** K's round on 2026-10-23: 8 menu boots and 6
game boots (Instant Play resume of Anguna on gpsp), all with adb, usbnet and
bootchart off (boots `001`–`014`). Numbers are medians on the kernel clock.
K judged the device times to match what the video showed, so no video times
were taken: pre-kernel time and power-on totals are **not measured**. The
experiments in "Confirmed by experiment" were run live over adb.

Build: StarFling 0.1.0 + task 1.1 instrumentation (`.fwu` `757848ea…`,
PR #3), Kodak 64 GB reference card, theme RetroRoomCovers, `firstCollection
= Main`.

## Bottom line

- **Menu:** 3.94 s from kernel clock start to a menu that accepts input.
  The target (D2) is ≤ 3.0 s from power-on, and pre-kernel time comes on
  top, so the menu path needs to lose at least ~1 s plus whatever U-Boot
  costs.
- **Game:** the emulator starts at 2.27 s on the kernel clock; gameplay
  comes later (emulator start, amp sleep, core and savestate load).
- **Biggest single levers, both measured:** the codec amplifier's 700 ms
  power-up sleep (~0.75 s, menu and game) and fkgpiod's `sleep(1)` holding
  up Instant Play (~0.55 s, game). Together with the quick menu's eager setup (0.22 s),
  S10share (0.34 s) and the menu animation (0.28 s), the measured,
  addressable time on the menu path is about 1.6 s before any kernel or
  U-Boot work.

## Method

- On-device: boot marks in the kernel log (init scripts, `.profile`,
  RetroFE), collected per boot into `/mnt/starfling-boot/NNN/`; optional
  bootchart. See `PHASE-1-BOOT.md` 1.1 and `DEVLOOP.md` section 7.
- Wall clock: K's 240 fps video, `docs/starfling/boot-timing-template.csv`.
- Pre-kernel time (BROM, SPL, U-Boot, kernel decompression) = video time to
  the first menu frame − kernel time at RetroFE's `menu first frame` mark.
- Report: `tools/starfling/boot-report.py <folder> --video <csv>`.

## Results from the timing round

| Measure (median) | Menu path (n=8) | Game path (n=6) |
|---|---|---|
| Power-on → menu / game (video) | not measured | not measured |
| Pre-kernel (BROM, SPL, U-Boot, decompression) | not measured | not measured |
| Kernel clock → menu first frame | 3.661 s | — |
| Kernel clock → menu accepts input | **3.943 s** | — |
| Kernel clock → game exec | — | **2.273 s** |

Boot-to-boot spread is small: most steps vary by under 10 ms across boots.

## Stage breakdown (medians, kernel clock, adb off)

| Stage | From → to | Menu ms | Game ms | Notes |
|---|---|---:|---:|---|
| Pre-kernel | power-on → kernel clock 0 | ? | ? | Not measured; needs video or a serial console (1.6) |
| Kernel | clock 0 → init | 558 | 558 | fbtft panel init ~146, USB host EHCI/OHCI ~100, pinctrl/serial ~76 |
| sysinit | init → rcS start | 209 | 207 | `mount -a` (FAT) ~115, `swapon` ~53, ~12 forked commands |
| S10share | | 343 | 344 | USB gadget setup, ~20 `mkdir -p`, `.fwu` check |
| Other S-scripts | | 361 | 365 | S50alsa-utils 111, S01first_boot 40, S02sysctl 40, S20urandom 29, S13 23, S40 20, S12 18, S04 17, S03 16, S11 14, S49 13, rest ~25 |
| Login + `.profile` to volume/brightness restored | rcS end → restored | 213 | 211 | `volume set` alone ~120 |
| `assembly_tests` | | 14 | 13 | |
| `instant_play load` | → frontend exec / game exec | 59 | **573** | Game: ~550 of it waits for fkgpiod (see below) |
| RetroFE exec → `main` | | 346 | — | Cold page-in of 22 libraries; 52 ms warm |
| Config import | `main` → config imported | 168 | — | 58 ms warm |
| SDL init | → sdl initialized | 866 | — | ~750 is the audio amp power-up sleep |
| Font cache, quick-menu setup, controls | → video initialized | 222 | — | `MenuMode::init()`: 13 fonts (5 × the 4 MB CJK fallback), images, zones; only needed on MENU. GStreamer is *not* initialised (`videoEnable = no` already skips it) |
| Splash, init thread, layout, fonts, collection, menu build | → menu first frame | 302 | — | Fonts ~53 |
| Menu onEnter animation | first frame → accepts input | 278 | — | |
| Emulator start → gameplay | game exec → game moving | — | ? | Not measured; includes the ~0.75 s amp sleep (measured live) |

**Game path: 0.55 s waiting for fkgpiod.** `instant_play load` runs
`keymap resume`, which writes to fkgpiod's FIFO. fkgpiod (started by
S11gpio) creates its uinput device and then calls `sleep(1)` in
`init_uinput()` before `init_gpio_mapping()` opens the FIFO. Until then
the FIFO has no reader, so the write blocks. In all 6 game boots, uinput
is created at 1.250 s (kernel log `input: ample as /devices/virtual/...`),
the FIFO opens about 1 s later, and `game exec` follows at 2.27 s. With
fkgpiod running, `keymap resume` takes 10 ms (live). The menu path does not
call `keymap` before RetroFE, so it does not wait.

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

## Top time sinks (measured medians, adb off)

| # | Sink | Menu ms | Game ms |
|---|---|---:|---:|
| 1 | Audio amp power-up sleep (kernel `msleep(700)` on first playback) | ~750 | ~750 (live test) |
| 2 | `keymap resume` waiting for fkgpiod's `sleep(1)` before its FIFO opens | — | ~550 |
| 3 | Kernel init (fbtft, USB host, probe) | 558 | 558 |
| 4 | Init scripts other than S10share (S50alsa-utils 111 the largest) | 361 | 365 |
| 5 | RetroFE exec, cold library page-in | 346 | — |
| 6 | S10share (USB gadget, `mkdir -p`s) | 343 | 344 |
| 7 | RetroFE splash → menu built (layout, fonts, collection) | 302 | — |
| 8 | Menu onEnter animation before input | 278 | — |
| 9 | Quick menu set up at startup (`MenuMode::init`) | 222 | — |
| 10 | Login + `.profile` (`volume set` ~120) | 213 | 211 |
| 11 | sysinit (`mount -a`, `swapon`, forks) | 209 | 207 |
| 12 | RetroFE config import (cold reads) | 168 | — |
| — | Pre-kernel; emulator start → gameplay | ? | ? |

## Levers, re-ranked

| Lever | Task | Est. saving | Confidence |
|---|---|---:|---|
| Warm the amp in the background early in boot (a short silent stream right after the codec probes), or open audio off RetroFE's main thread; never shorten the kernel sleep without listening for pops | 1.3 / 1.5a | ~0.75 s menu and game | High (measured on both) |
| Set up the quick menu on first MENU press instead of at startup (and on every return from a game, `unloadSDL`) | 1.4 | ~0.2 s | High (measured span; attribution from code) |
| Drop GStreamer linkage (video is off) to cut library page-in | 1.4 | part of the 346 ms exec page-in | Low |
| Userspace fast path: frontend straight from init, defer late services (`alsactl`, sysctl, urandom, system-stats), fewer forks in `.profile` | 1.3 | 0.4–0.7 s | Medium |
| Prefetch RetroFE and its libraries in the background during kernel/sysinit idle time, or trim libraries | 1.3 / 1.4 | 0.1–0.2 s | Medium |
| Shorter or no onEnter animation for the first menu | 1.4 | up to 0.27 s | Medium (theme) |
| Kernel trim: USB host off the boot path (1.5a), fbtft init, logo | 1.5 | 0.1–0.3 s | Medium |
| Open fkgpiod's FIFO before its uinput `sleep(1)` (or drop the sleep), or make `keymap resume` not wait | 1.7 | ~0.55 s game | High (cause confirmed on 6/6 boots) |
| USB gadget setup off the boot path (S10share), `mkdir -p` only when missing | 1.3 | 0.2–0.3 s | Medium |
| Pre-kernel (U-Boot) | 1.6 | ? | Not measured yet; measure in 1.6 |

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
