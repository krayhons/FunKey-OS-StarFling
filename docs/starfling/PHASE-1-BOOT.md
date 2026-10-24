# Phase 1 — Boot-Time Optimization (agent brief)

Read `plan.md` first. This file is the working brief for Phase 1 and the
framework the coding agent follows. Every time estimate below is a
**hypothesis from reading the code**, not a measurement. Task 1.2 replaces
them with real numbers, and the plan is re-ranked from those numbers before
any optimization work starts.

## Goal

| Path | Baseline (drum86, K's stopwatch) | Target |
|---|---|---|
| Power-on → interactive menu (accepts input) | ~6 s | **≤ 3.0 s** (median of 10 cold boots) |
| Power-on → gameplay frame, resuming a game via Instant Play | not yet measured | **≤ 3.0 s** for the reference core |

Definitions:
- **T0** is the frame where the power switch/button is actuated (phone video).
- **T_menu** is the first frame where the menu is on screen *and* responds to a
  D-pad press.
- **T_game** is the first frame of moving gameplay after resume.
- First boot after flashing (partition resize) is excluded.
- All measurements use one **reference SD card** (same card, same ROM set,
  same Favorites/Recently Played state, default theme). Card speed changes
  results a lot, so it never changes mid-phase. Record the card model.

Behaviour that must not change: menu if powered off in a menu (RetroFE
`rememberMenu = true`), the same game if powered off in a game
(`instant_play load` runs before the frontend). Both already exist upstream.

## The boot chain as it is today (from the repo)

| Stage | What runs | Where it lives |
|---|---|---|
| BROM → SPL | Allwinner V3s boot ROM loads SPL from SD offset 8 KiB; SPL initialises DRAM (`CONFIG_DRAM_CLK=360`) | U-Boot built by the **Recovery** tree: `Recovery/board/funkey/uboot.config`, tarball `u-boot-FunKey-1.00` |
| U-Boot | `bootdelay=0`. `bootcmd` runs `part list` (find bootable partition), `check_keys` (I2C probe + key read for FN+START → Recovery, `delay=1`), then `load` zImage and DTB from ext4 `/boot` on the flagged partition, `bootz` | Env: `FunKey/board/funkey/rootfs-overlay/etc/u-boot.env` (also baked in as default env) |
| Kernel | DrUm78 `v1.0-rg-nano` tarball, **LZO** compressed, DTB `sun8i-v3s-funkey`. Cmdline: `console=ttyS0,115200 ... rootwait ... rootfstype=ext4 ... ro quiet`. Display is an **ST7789V over SPI via fbtft**, with fbcon and `CONFIG_LOGO=y`. Also built in: USB EHCI/OHCI host, MUSB OTG, USB audio, OSS emulation, SCSI/sd, SSD1307 OLED, PCF8563 RTC, `HIBERNATION` + `PM_DEBUG`, networking. `PRINTK_TIME=y` already | `FunKey/board/funkey/linux.config` (a 143-line defconfig fragment) |
| init (sysinit) | BusyBox init. `inittab` sysinit: mount proc, `mount -a` (includes the FAT share on `/mnt`), `swapon -a`, symlinks, hostname, **syslogd, klogd**, then `rcS` | `rootfs-overlay/etc/inittab`, `etc/fstab` |
| rcS (serial) | S01first_boot (`fw_printenv`, `hwclock`), S03rclocal, S04modules, **S10share** (USB gadget via configfs + `modprobe libcomposite`, ~20 `mkdir -p` of ROM/collection dirs every boot, `.fwu` check), S11gpio (fkgpiod), S12low-bat-check, S13system-stats, S20urandom, S40/S41/S42 network/dhcp/dropbear (skip unless `/mnt/usbnet`), S49audio (polling daemon), S50alsa-utils (`alsactl restore`), S52audioinit | `rootfs-overlay/etc/init.d/`, `usr/local/sbin/` |
| Login shell | `inittab` respawns `-/bin/login -f root` on the console → bash → `/etc/profile` → `/root/.profile` | `rootfs-overlay/root/.profile` |
| `.profile` | `volume set`, `brightness set`, `assembly_tests` (reads U-Boot env, exits), **`instant_play load`** (resumes a game, blocks until it exits), then `frontend init &` → RetroFE | same |
| RetroFE | RetroFE-FunKey-1.1.4 + 19 Starling patches. Shows the theme's `splash.xml` ("Loading..."), loads layout `RetroRoomCovers` (fallback in `settings.conf`, real choice in `layout.conf`), fonts, `meta.db` (7 MB SQLite, `initMetaDb = no`), builds the Main collection, restores the last menu | `FunKey/package/retrofe/`, `rootfs-overlay/usr/games/` |

Two findings worth fixing regardless of timing:

1. **`CONFIG_PM_STD_PARTITION="/dev/mmcblk0p2"` points the hibernation
   partition at the root filesystem.** At boot the kernel checks that partition
   for a resume signature, and a hibernate would overwrite the rootfs. Either
   disable `CONFIG_HIBERNATION` or point it at swap (`p3`) with `noresume` until
   snapshot boot is deliberately explored (task 1.9).
2. **`/mnt/adb` or `/mnt/usbnet` adds a fixed `sleep 5` inside S10share**
   (`usb_gadget`, `adb`). That blocks boot by 5 s or more whenever either flag
   is set. The dev loop uses adb, so this must be moved off the boot path or
   the timings will be wrong.

## Rough time budget (hypothesis, to be replaced in 1.2)

| Stage | Guess today | Target budget |
|---|---|---|
| BROM + SPL + DRAM init | 0.3–0.5 s | 0.3 s |
| U-Boot (env, I2C key check, ext4 loads) | 0.4–0.9 s | 0.3 s |
| Kernel (decompress → init) incl. fbtft panel init | 1.0–1.6 s | 0.9 s |
| Userspace init → frontend exec | 1.0–1.8 s | 0.3 s |
| RetroFE start → interactive menu | 1.0–2.5 s | 1.2 s |
| **Total to menu** | **~6 s** | **≤ 3.0 s** |

For the game path, everything up to "userspace init" is shared; then
`instant_play load` → emulator start → core and ROM load → savestate load must
fit in about 1.5 s.

## Measurement levels (answer to "what is needed?")

No special hardware is required for Phase 1. Serial is a nice-to-have.

| Level | Needs | Gives | Use |
|---|---|---|---|
| **0** | A phone that records 240 fps slow-motion video; a USB cable | Wall-clock T0 → T_menu / T_game. On-device timestamps (boot marks from the init scripts and RetroFE in the kernel log, next to the kernel's own `PRINTK_TIME` lines; optional BusyBox bootchart) saved to `/mnt/starfling-boot/NNN/` and read on the PC as a USB drive. **Pre-kernel time (BROM + SPL + U-Boot + decompress) = video time to the first menu frame − kernel time at RetroFE's `menu first frame` mark.** | Required. K's part: power-cycle and film; about 1 minute per boot |
| **1** | Level 0 + Google's Windows `adb.exe`, called from WSL2 (`/mnt/c/platform-tools/adb.exe`), with `/mnt/adb` set on the device. usbipd-win does not work with the RG Nano (`DEVLOOP.md` section 4) | Claude Code can `adb shell`, `adb push` builds of single files (scripts, RetroFE binary), pull logs, and run `reboot` itself | Strongly recommended; turns most iterations into minutes with no reflash |
| **2** | A 3.3 V USB-to-UART adapter (CP2102, CH340 or FTDI, about $5–10), soldering or pogo pins, opening the RG Nano | Live SPL/U-Boot/kernel console with timestamps; rescue when a build does not reach userspace | Optional. Only if U-Boot work (1.6) stalls. UART pad locations on the RG Nano board are **not confirmed** by anything found so far; find them before buying. Never use a 5 V adapter |

The agent cannot press the power button or see the screen. Every
measurement round is: agent prepares the build or pushed change → K runs
the boot script below → agent reads the logs from `/mnt/starfling-boot/` and
K reports the video times.

**Measurement round (K):** for each of the 10 boots: power off, wait 5 s,
start filming, power on, press D-pad right once the menu appears, stop. Read
the times from the video frame counter. Repeat with a game resumed. The exact
steps are in `DEVLOOP.md` section 7; the CSV template is
`docs/starfling/boot-timing-template.csv`.

## Levers and estimated savings

Savings are per lever, measured against today's boot, and they overlap; they
do not simply add up.

### Items K asked about

| Item | What it is here | Est. saving | Recommendation |
|---|---|---|---|
| (a) Boot splash / logo | Kernel `CONFIG_LOGO` + fbcon drawing over the SPI panel; RetroFE `splash.xml` page with a fade animation before the main layout | 0.05–0.3 s (kernel); 0.2–0.8 s (RetroFE splash) | Drop the kernel logo and fbcon from the boot path (keep fbcon for Recovery). Replace the RetroFE splash with one static frame drawn immediately, or skip it. A single early static image keeps the boot from *feeling* slow |
| (b) USB gadget at boot | S10share builds the configfs gadget and loads `libcomposite` every boot; `sleep 5` if adb/usbnet flags are set | 0.1–0.4 s normally; 5 s+ with flags | Defer: build the gadget in the background after the frontend starts, or on demand when MOUNT USB is chosen or a cable is detected. Keep the `.fwu` check on the fast path (one glob, a few ms) |
| (c) Unused kernel drivers/modules | USB host EHCI/OHCI, SSD1307 OLED, `FB_SIMPLE`, SCSI/sd, OSS emulation, `HIBERNATION`/`PM_DEBUG`, `PERF_EVENTS`, `CGROUPS`, extra crypto, PCF8563 RTC probe (if the RG Nano has no PCF8563, the probe costs I2C timeouts) | 0.2–0.6 s (probe time + smaller image to load and decompress) | Trim in small, separately measured steps. **USB-C audio is required (D9)**: keep it, but move it off the critical path per task 1.5a. Make libcomposite built-in. Try LZ4 vs LZO vs uncompressed kernel |
| (d) Filesystem checks | No fsck runs on the normal path today: root is mounted read-only, and the FAT dirty-bit check in `share` only runs when `/mnt` is not already mounted (it is, by `mount -a`) | ~0 s | Nothing to cut. Keep it that way: do not add fsck to the boot path |
| (e) Read-only squashfs root | Root is already mounted read-only (ext4, `ro`). Squashfs (LZ4) would cut cold-read I/O for binaries and theme files | 0.1–0.4 s | **Defer to 1.9 (gated).** Several scripts remount root read-write (`rw`/`ro`: the gpsp Instant Play path moves `/etc/asound.conf`; first_boot runs `resize2fs`; theme changes may write under `/usr/games`), and `.fwu`/swupdate writes an ext4 image to `p2`. The saving does not justify that churn unless 1.3–1.7 miss target |
| (f) Drop `.fwu`/OTA compatibility | The `.fwu` check costs milliseconds; compatibility only matters if the rootfs format changes | ~0 s | Keep it (D7). Revisit only together with (e) |

### Bigger levers not on that list

| Lever | Est. saving | Notes |
|---|---|---|
| **Userspace fast path**: start the frontend (or the Instant Play game) straight from a minimal init script instead of rcS → login → bash → `.profile`; move syslogd/klogd, low_bat_check, system_stats, audio daemon, `alsactl restore`, `hwclock`, urandom, dropbear checks to a background "late" stage; skip the ~20 `mkdir -p` calls unless a marker is missing | 0.5–1.2 s | Single-core Cortex-A7: every fork/exec of a shell tool is several ms. Volume restore must still run before audio is heard; low-battery shutdown must still start within a few seconds |
| **RetroFE startup**: profile with timestamps; skip/flatten the splash; open the 4 MB CJK fallback font lazily (Starling 0017/0018 open it at startup and per font size); cache collection scans keyed on directory mtime (generalises Starling `ANALYSIS.md` item 1); defer `meta.db` open if not needed for the first screen; check theme image decode cost (RetroRoomCovers loads cover art) | 0.5–2.0 s | Depends heavily on library size and on which menu was last open. If the last menu was Favorites or a big system, restoring it triggers a full ROM-directory scan today |
| **Kernel cmdline**: drop `console=ttyS0` in production builds (keep it in a debug variant), `loglevel=0`, preset `lpj=` if calibration shows in dmesg, keep `quiet` | 0.05–0.3 s | Any kernel print at 115200 baud costs ~87 µs per character |
| **U-Boot**: check SPL/U-Boot MMC bus width and clock; avoid the ext4 path for kernel/DTB if measurably slow (e.g. one combined image or raw offset); trim the I2C key-check to a single read; silence console output | 0.1–0.4 s | Must keep FN+START → Recovery and the bootable-flag partition selection (Recovery's EXIT uses it) |
| (Gated) U-Boot **Falcon mode** (SPL boots the kernel directly) | 0.3–0.7 s | Recovery key logic would have to move into SPL. Only if still over target |
| (Gated) **Snapshot resume** (boot by resuming a hibernation image of a system sitting at the menu) | could reach ~1.5–2 s to menu | 64 MB RAM, 128 MB swap on `p3`. High risk and complexity; an experiment, not a commitment |

## Starling-specific features and their boot-time effect

Starling adds only frontend features plus build/CI fixes. Everything else is
stock drum86 RG Nano FunKey OS. Instant Play is upstream FunKey, not Starling.

| Feature (patches in `FunKey/package/retrofe/`) | Boot-time effect |
|---|---|
| Favorites (0001–0016): Y to mark, Favorites as first Main-menu entry, aggregate collection across systems | None if the last menu was not Favorites. If it was, restoring it rebuilds the aggregate, which scans every favorited system's ROM directory; Starling's own `ANALYSIS.md` estimates "seconds" for 1,000+ ROM libraries. Biggest Starling risk to the target |
| UTF-8 text and CJK fallback face (0017) | Opens `DroidSansFallbackFull.ttf` (~4 MB) alongside each theme font size. Likely tens to low hundreds of ms on a cold card. Fix: open lazily on the first non-Latin code point |
| Bilingual quick-menu text (0018) | Opens the CJK font at several sizes for the MENU overlay. Fix the same way, or only when the menu first opens |
| Recently Played (0019) | Reads a small list file; restoring that menu merges per-system entries. Small unless it triggers system scans |
| CI and Docker fixes | No runtime effect |

## Tasks

Each task: one branch, one PR, before/after numbers in the PR description,
regression checklist ticked. Order is fixed for 1.1–1.2; after that, 1.2's
report decides the order.

### 1.1 Instrumentation (no behaviour change)

As built (2026-10-23). Two changes from the original plan, both for lower
overhead and less to maintain:

- **One build, switched at runtime, instead of a separate debug build.**
  Instrumentation is on while the folder `/mnt/starfling-boot/` exists on
  the share drive. Without it, each hook is a single file test and the boot
  behaves as before (checked on the device: no marks, no collector, kernel
  log settings untouched).
- **Marks go to the kernel log (`/dev/kmsg`), not `/run/bootmarks`.** They get
  the kernel's microsecond timestamps on the same clock as kernel messages,
  instead of the 10 ms steps of `/proc/uptime`. `rcS` sets
  `printk_devkmsg=on` when enabled; the default rate limit (10 per 5 s)
  would drop most marks.

What is there:

- `/usr/local/lib/bootmark` (sourced; a fork+exec costs about 4.5 ms on the
  RG Nano, a mark about 0.25 ms) and a `bootmark <label>` command for ad-hoc
  use. Marks: rcS start (after `/mnt` is mounted by `mount -a`), the start of
  each S-script, rcS end, `.profile` steps, frontend exec, game exec.
- RetroFE patch `0020-starfling-boot-marks.patch`: main, config imported, SDL
  and video initialised, splash loaded and first frame, init thread (input,
  `meta.db`), each font load with its duration, layout loaded, collection
  loaded, menu built, menu first frame, menu accepts input, first input
  handled.
- `starfling-boot-collect`, started by rcS at nice 19: 30 s after rcS ends it
  saves `dmesg.txt`, `retrofe.log`, `info.txt` (adb/usbnet/bootchart flags,
  version, cmdline) and, if requested, `bootchart.tgz` to
  `/mnt/starfling-boot/NNN/`, then shows "Boot data NNN saved".
- Optional bootchart: a file named `bootchart` in the folder. BusyBox
  `bootchartd` (and seamless gzip for its `tar -z`) is now in every build,
  but runs only on request.
- `tools/starfling/boot-report.py` turns the folders and K's video CSV into
  per-boot timelines and per-path medians.
- **Accept:** a debug build produces a complete timeline; production build
  behaviour unchanged; overhead under 20 ms.

### 1.2 Baseline and bottleneck report
- 10 cold boots to menu and 10 to a resumed game, on the reference card, for
  (i) stock Starling and (ii) K's drum86 build if available.
- Output `docs/starfling/BASELINE.md`: per-stage medians, the top 10 time
  sinks, and a re-ranked lever list with expected savings.
- **Stop and get K's go-ahead before 1.3.**

### 1.3 Userspace init restructure
- New fast path: essential mounts → `/mnt` → `.fwu` check → volume/brightness
  restore → Instant Play or frontend. Everything else in a background late
  stage after the frontend is up.
- Replace the console-login launch with a dedicated inittab entry that keeps
  the same environment (`HOME=/mnt/FunKey`, `RETROFE_HOME`, PATH) and the same
  respawn behaviour.
- USB gadget deferred (lever (b)); adb/usbnet `sleep 5` moved off the boot path.
- Directory creation only when a marker file is missing.
- **Accept:** userspace stage ≤ 0.3 s to frontend exec; full regression list
  passes; low-battery shutdown still triggers; serial console login still
  available in debug builds.

### 1.4 RetroFE startup
- From 1.1's timestamps, fix the largest RetroFE costs: splash, lazy CJK
  font, collection-scan cache, `meta.db`, image decode.
- New patches go after 0019 in the series; never edit an applied patch without
  `retrofe-dirclean` (the README explains why).
- **Accept:** RetroFE start → interactive ≤ 1.2 s on the reference card from
  the Main menu, and a measured number from Favorites and from a large system.

### 1.5 Kernel trim and cmdline
- One driver group per commit, measured. Fix `PM_STD_PARTITION`/hibernation.
  Try compression variants. Production vs debug cmdline.
- Kernel and DTB live in `p2:/boot`, so they ship in the `.fwu`; no card
  reflash is needed for kernel-only changes.
- **Accept:** kernel stage ≤ 0.9 s; display, buttons, audio, battery, USB
  mass storage, USB-C audio (if kept) all work.

### 1.5a USB-C audio off the critical path (D9)
The RG Nano has no 3.5 mm jack, so USB-C dongles are the only headphone
route. Today USB host, USB audio and OSS emulation are built into the kernel
and probe during boot. `S49audio` is a shell loop that wakes every second to
check `/proc/asound/card1` and rewrites `/mnt/FunKey/.asoundrc`. `S52audioinit`
runs at boot. Three complementary approaches, in this order:

1. **Find out what is actually used.** With a dongle attached, record which
   host controller enumerates it (MUSB in host mode vs EHCI/OHCI) and which
   drivers bind. Remove whatever never binds on the RG Nano. Measure probe
   cost of each with `initcall_debug` in a debug build.
2. **Defer loading.** Build USB host and `snd-usb-audio` as modules and load
   them in the background late stage, after the menu or game is up. A dongle
   plugged in at power-on is then picked up about a second after the menu
   appears.
3. **Recode the switching to be event-driven.** Replace the 1-second polling
   loop with a hotplug handler (BusyBox mdev or a tiny uevent listener) that
   writes `.asoundrc` and restores volume only when a sound card appears or
   disappears. This removes the per-second fork cost and the boot-time script.

**The resume-path exception.** ALSA cannot move an already-open stream to a
new card, so a game resumed before the dongle is ready would play through the
speaker. Fix: when Instant Play saves at power-off, also record whether a USB
card was active. On the next boot, only if that flag is set, load the USB
audio modules on the fast path and wait up to a bounded time (start with
800 ms, tune from measurements) for the card before launching the game. Normal
boots pay nothing. Making emulators reopen audio on hotplug is a per-core
phase item, logged in the backlog.

- **Accept:** no USB audio probe on the menu boot path; dongle present at
  boot works in the menu within ~1.5 s of T_menu; plug/unplug at runtime
  switches output; resume with a dongle plays through the dongle; resume
  without one keeps the 3.0 s target; volume follows the active card.

### 1.6 U-Boot
- U-Boot is built by the Recovery tree and written at SD offset 8 KiB, so it
  needs a full image flash (or a `dd` to the card offset). Test on a spare card.
- Measure first (pre-kernel time from Level 0). Only change what the numbers
  justify.
- **Accept:** pre-kernel time ≤ 0.6 s; FN+START still enters Recovery;
  Recovery's EXIT still returns to `p2`.

### 1.7 Instant Play resume path
- Make the game path skip everything the menu path skips; start the emulator
  as early as the fast path allows. Choose one **reference core** with K
  **GBA via gpsp (D10)**. It also exercises the `rw`/asound special case in
  `instant_play`, which must keep working with task 1.5a's USB audio changes.
- Per-core startup and savestate speed is out of scope here; that belongs to
  the per-core phases.
- **Accept:** T_game ≤ 3.0 s for the reference core.

### 1.8 Regression pass and release
- Run the checklist below on the reference card and on a fresh-flashed card
  (first-boot path). Write `## StarFling-1.0.0` in `CHANGELOG.md` with before
  and after numbers.

### 1.9 (Gated) experiments
- Squashfs root, Falcon mode, snapshot resume. Only with K's approval and
  only if the target is missed after 1.3–1.7.

## Regression checklist

- [ ] Cold boot to menu; last menu position restored
- [ ] Power off in game → power on resumes the same game; exiting the game
      returns to the menu
- [ ] FN+START at power-on enters Recovery; EXIT RECOVERY returns to normal
- [ ] MENU → MOUNT USB shows the drive on a PC; eject returns to the menu
- [ ] Copy a `.fwu`, eject → update installs and keeps games, saves, favorites
- [ ] Favorites: mark, unmark, enter Favorites, launch from Favorites
- [ ] Recently Played lists the last game
- [ ] Volume and brightness persist across reboot
- [ ] Low battery shuts the device down cleanly
- [ ] Theme change from the quick menu persists
- [ ] Screenshot (FN+UP) and the statistics overlay work
- [ ] USB-C audio dongle: present at boot, hot-plugged in menu, hot-plugged in
      game, and present on Instant Play resume
- [ ] First boot on a freshly flashed card completes (resize, swap, share)

## Risks

| Risk | Mitigation |
|---|---|
| Starling has not run on hardware since 3.0.0 | Phase 0.2 proves it boots before any boot-time work |
| A change stops the device reaching userspace | SD boot means reflash from Windows; keep the known-good card; Recovery on `p1` is untouched except in 1.6 |
| Battery-latched unresponsive state (noted in the Starling README) | Briefly disconnect the battery; document in `DEVLOOP.md` |
| Timing noise between boots | Medians of 10 boots, same card, same state, device at room temperature and charged |
| WSL2 specifics | Repo on the WSL ext4 filesystem; Ubuntu 22.04 (24.04 lacks `python3-distutils`); Windows `adb.exe` for adb (usbipd-win fails); flash cards from Windows (balenaEtcher) |

## Backlog (not in Phase 1)

- Faster shutdown (upstream targets about 3 s); it affects how quickly
  Instant Play can save.
- Earlier first pixel (draw a static frame from the kernel or U-Boot).
- Per-core startup and savestate speed (Phases 2..n).
- Emulators reopen their audio device when a USB-C dongle is plugged or
  unplugged mid-game (per-core phases).
- Lighter launcher (later phase).
- Leaving Recovery sometimes hangs on an inverted (black/white swapped) boot
  logo and needs a power cycle: 2 of about 9 exits so far, including the
  automatic restart after a `.fwu` install (`plan.md`, task 0.5). Upstream
  behaviour. Look at it before or with 1.5/1.6; a serial console (Level 2)
  would show where it stops.
