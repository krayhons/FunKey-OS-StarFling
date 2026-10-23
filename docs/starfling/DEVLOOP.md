# StarFling dev loop

How to build StarFling on Windows (WSL2), get it onto the RG Nano, and iterate
over adb without reflashing. Written from the repository's scripts, then
checked on K's RG Nano on 2026-10-23: sections 3 to 6 match the device except
where they say otherwise. Correct this file as soon as a step behaves
differently on the device.

## 1. Build host (WSL2, task 0.1)

One-time setup:

1. In PowerShell: `wsl --install -d Ubuntu-22.04`. Use 22.04, not 24.04
   (24.04 dropped `python3-distutils`, which buildroot needs).
2. Give WSL2 enough CPU and memory. Create `%UserProfile%\.wslconfig`:

   ```ini
   [wsl2]
   processors=<number of cores>
   memory=12GB
   swap=8GB
   ```

   Also stop WSL from appending the Windows PATH: its entries contain spaces
   (`Program Files`), and buildroot refuses to build with spaces in PATH. In
   Ubuntu, put this in `/etc/wsl.conf`:

   ```ini
   [interop]
   appendWindowsPath=false
   ```

   Then `wsl --shutdown` and reopen Ubuntu. WSL2's default memory cap is half
   of RAM; parallel C++ jobs (RetroFE, emulators) can run out of memory
   with less, which makes the build fail or crawl.
3. In Ubuntu, install the packages from the README "Natively" section, then
   clone into your Linux home directory, **not** under `/mnt/c`:

   ```bash
   cd ~
   git clone --recurse-submodules https://github.com/krayhons/FunKey-OS-StarFling.git
   cd FunKey-OS-StarFling
   make all
   ```

   Skip `make sdk`. The build downloads a prebuilt cross-toolchain
   (`BR2_TOOLCHAIN_EXTERNAL_URL` in the defconfigs), so `make sdk` is only for
   publishing a toolchain.

Outputs land in `images/`; `make -s print-artifacts` prints their names. If the
build fails, `br.log` in the repo root has the full log.

### Making builds faster

The first build is slow because it compiles everything once. Later builds
are much faster if you keep the build state:

| What | Effect |
|---|---|
| Repo on the WSL ext4 filesystem (`~/`), not `/mnt/c` | The biggest single factor. `/mnt/c` goes through a network-style file bridge and is several times slower for builds |
| `.wslconfig` `processors` set to all cores | Buildroot runs `make -j` with cores + 1 jobs by default (`BR2_JLEVEL=0`) |
| Keep `download/` | Source tarballs are cached there (`BR2_DL_DIR`). Never `make distclean` unless you mean to fetch everything again |
| ccache | Already on (`BR2_CCACHE=y`, cache in `~/.buildroot-ccache`). It speeds up a rebuild after a clean |
| Rebuild one package instead of everything | `make FunKey/retrofe-rebuild update` rebuilds RetroFE and makes a new `.fwu`. Replace `retrofe` with any buildroot package name. Overlay-only changes (scripts under `rootfs-overlay/`) need only `make update` |
| Avoid `make clean` | It wipes the Recovery and FunKey outputs, so the next build is a first build again |
| Push single files over adb (section 4) | For scripts and the RetroFE binary, no image or `.fwu` is needed at all |

Expected: first build 1.5 to 3 h, a one-package rebuild plus `.fwu` a few
minutes.

## 2. Getting a build onto the card

- **Full image** (first install, or anything touching Recovery or U-Boot):
  write `images/FunKey-sdcard-StarFling-*-RG_Nano.img` to the card from Windows
  with balenaEtcher. This erases the card. Copy it to Windows first, for
  example `cp images/*.img /mnt/c/Users/<you>/Downloads/`.
- **Update** (rootfs and kernel only, keeps games and saves): MENU → MOUNT USB,
  copy `images/FunKey-rootfs-StarFling-*-RG_Nano.fwu` to the drive, eject.
  This needs mass storage, which is off while adb is on (see below).

Keep one known-good card at all times. Recovery and the battery-latch reset
are in the README "Recovery" section.

## 3. Enabling adb

adb is turned on by an empty file named `adb` at the root of the share drive
(`/mnt/adb` on the device). At boot, `usb_gadget` sees it and starts `adb`
instead of the mass-storage gadget.

1. MENU → MOUNT USB, and open the drive in Windows.
2. Create an empty file named exactly `adb`, with no extension. Explorer hides
   extensions by default and will create `adb.txt`, so use PowerShell:
   `New-Item E:\adb -ItemType File` (replace `E:` with the drive letter).
3. Eject, unmount on the device, and power-cycle.

While `/mnt/adb` exists, keep these effects in mind:

- **No mass storage.** The adb gadget (`ADB+CDC`) replaces the mass-storage
  gadget, so MOUNT USB will not show the drive on the PC. Use `adb push`/`pull`
  instead, or remove the flag.
- **Boot is at least 5 s slower.** `adb` runs `sleep 5` before binding the USB
  controller, on the boot path (S10share). **Never record a boot timing with
  the flag set** until Phase 1 task 1.3 moves this off the boot path.

To turn adb off: `adb shell rm /mnt/adb`, then power-cycle. If adb is not
reachable, use Recovery (FN+START at power-on) → USB, delete `adb` from the
drive, then EXIT RECOVERY.

## 4. Reaching the device from WSL2 (Windows adb.exe)

Checked on K's RG Nano on 2026-10-23 (Starling 3.1.3): use Google's Windows
`adb.exe` and call it from WSL. No USB passthrough is needed, and adb comes
back by itself after every reboot (about 10 s after `adb shell reboot`).

One-time:

1. Download [platform-tools for Windows](https://developer.android.com/tools/releases/platform-tools)
   and unzip it to `C:\platform-tools`. With `/mnt/adb` set, Device Manager
   shows the RG Nano as "ADB Interface" plus a CDC serial port (COM4 on K's
   PC); no driver install was needed.
2. In Ubuntu, add an alias to `~/.bashrc`:

   ```bash
   alias adb=/mnt/c/platform-tools/adb.exe
   ```

3. `adb devices` should list one device (K's: `12c000014ae74908`).

Notes:

- `adb.exe` is a Windows program, so local paths in `adb push`/`pull` must be
  Windows paths. For files in the WSL tree, convert with `wslpath -w`:
  `adb push "$(wslpath -w FunKey/output/target/usr/games/retrofe)" /usr/games/`.
  `\\wsl.localhost\...` paths work. `adb pull` into the current WSL directory
  also works.
- Run only one adb server. Do not also install or start Linux `adb` in WSL;
  both use port 5037.

### usbipd-win does not work with this device

`usbipd attach --wsl` (usbipd-win 5.x, WSL kernel 6.18) gets as far as
enumerating the device in WSL (`cdc_acm ... ttyACM0`), then the USB/IP
connection closes within about 40 ms. The device then disappears from Windows
USB entirely and stays gone until it is rebooted. With `--auto-attach` this
repeats on every boot. The gadget scripts (`usb_gadget`, `adb`, `S10share`) are
unchanged from upstream FunKey (2020 to 2022) and the kernel is DrUm78's
`v1.0-rg-nano`, so this is probably not Starling-specific; the likely cause is
the device's gadget not surviving the USB reset that attach performs. Not
investigated further, because Windows `adb.exe` covers the dev loop. If a
device is still attached or bound, stop with Ctrl+C and
`usbipd unbind --busid <BUSID>` in an admin PowerShell.

## 5. The loop

| Task | Command |
|---|---|
| Shell | `adb shell` |
| Make the rootfs writable / read-only again | `adb shell rw` … `adb shell ro` |
| Replace a script | `adb shell rw && adb push FunKey/board/funkey/rootfs-overlay/usr/local/sbin/<script> /usr/local/sbin/ && adb shell ro` |
| Replace the RetroFE binary | `adb shell rw && adb push FunKey/output/target/usr/games/retrofe /usr/games/ && adb shell ro`, then `adb shell pkill retrofe` (the `frontend` loop restarts it within about 0.5 s) |
| Pull logs | `adb pull /mnt/frontend-last-exit.log`, `adb shell dmesg > dmesg.txt`, `adb pull /mnt/starfling-boot/` (section 7) |
| Reboot | `adb shell reboot` |

Always `ro` before a power-off. A rootfs left read-write when the battery is
pulled can be corrupted. If `ro` prints `/ is still read-write` and exits 1,
something has a file on `/` open for writing (the remount fails with
"Resource busy"); stop it and run `ro` again, or reboot cleanly with
`adb shell reboot`. Files pushed this way stay on the rootfs only until
the next `.fwu` or image overwrites them, so commit the change to the repo
and rebuild before relying on it.

The agent can do all of this itself once `adb devices` lists the device. It cannot
press the power button or see the screen; you do the power cycles and the
phone-video timing (see `PHASE-1-BOOT.md`, "Measurement levels").

## 6. Phase 0 hardware check (task 0.2)

On a spare card flashed with the stock Starling 3.1.3 image (or StarFling
0.1.0, which is the same code renamed):

- [Y] Boots to the RetroFE menu (first boot resizes partitions and takes longer)
- [Y] D-pad and A/B respond; a game launches and exits back to the menu
- [Y] Power off in a game, power on: the same game resumes
- [Y] MENU → MOUNT USB shows the drive on Windows
- [Y] FN+START at power-on enters Recovery; 
- [Y] EXIT RECOVERY boots normally (6 of 7 tries; the first try stayed in Recovery and needed a hard reset, the next 6 rebooted normally. Task 0.5)
- [Y] With `/mnt/adb` set: `adb shell`, `adb push`, `rw`/`ro` all work from WSL2 (via Windows `adb.exe`, section 4; usbipd fails)
- [Y] Note the card model; it becomes the Phase 1 reference card - Card is Kodak64g

Record the results, and anything that differs from this file, in a handoff
note under `docs/starfling/handoff/`.

## 7. Boot timing data and measurement rounds (Phase 1.1)

### Turning boot timing on and off

Boot timing is on while a folder named `starfling-boot` exists at the root
of the share drive (`/mnt/starfling-boot` on the device). Every boot then
writes a folder `starfling-boot/NNN/` about 40 s after power-on and shows
**"Boot data NNN saved"** on screen. Without the folder nothing is recorded
and the boot behaves as before.

- On: MENU → MOUNT USB, create the folder `starfling-boot` in Explorer,
  eject. Or `adb shell mkdir /mnt/starfling-boot`.
- Off: delete the folder.
- Bootchart (optional, never on timing boots): also create an empty file
  `starfling-boot\bootchart` (PowerShell: `New-Item E:\starfling-boot\bootchart -ItemType File`).

Each `NNN/` holds `dmesg.txt` (kernel log with all boot marks), `info.txt`
(flags, version, cmdline), `retrofe.log` and, with bootchart on,
`bootchart.tgz`. Numbers count up from `001`; deleting the `NNN` folders
starts again at `001`.

Make a report on the PC (WSL) from a copy of the folder:

```bash
python3 tools/starfling/boot-report.py <copy of starfling-boot> --video <your CSV> --out report.md
```

### Agent-run rounds (autoround)

For changes that do not need a human at the screen, the agent can run a
round itself over adb, with adb off during the boots:

```bash
adb shell 'echo 10 > /mnt/starfling-boot/autoround; rm /mnt/adb; sync; reboot'
```

Each boot saves its data, lowers the count and reboots (about 40 s per
boot). The last one recreates `/mnt/adb`, so adb is back on the boot
after; that boot is also saved but has `adb=1` and the report skips it.
For a game round, start with a resumed game running: the collector puts
Instant Play's file back before each reboot, so every boot resumes the
same savestate.

These are warm reboots, not power-ons. On the kernel clock they match
K's cold boots (menu accepts input 3.93 and 4.04 s vs a cold median of
3.94 s), but they say nothing about pre-kernel time. If a boot hangs, the
round stops there, without adb; K then deletes `autoround` and recreates
`adb` over MOUNT USB (or FN+START → USB MOUNT).

### Measurement round (K)

A timing boot must have **no `adb` file**, no `usbnet` file and no
`bootchart` file on the drive: adb and usbnet add a fixed 5 s, and bootchart
sampling slows everything. The report skips boots with any of them.

Before the round:

1. Make sure the build under test is installed (the agent says which `.fwu`
   or image).
2. MENU → MOUNT USB. On the drive: delete `adb` if present; create the
   folder `starfling-boot` if missing, and delete any `NNN` folders inside
   it (keep the folder); make sure there is no `bootchart` file in it.
   Eject on the PC, then exit MOUNT USB on the device.
3. Charge the device and keep it at room temperature. Use the reference card
   (Kodak 64 GB) with the same ROMs, Favorites and Recently Played as before.
4. Copy `docs/starfling/boot-timing-template.csv` and fill in the `round`
   column with the name the agent gives you.

Menu path, 10 boots:

1. Be in the Main menu, then power off. Wait 5 s.
2. Start the phone recording at 240 fps, with the screen and the power
   switch both in frame.
3. Power on.
4. As soon as the menu appears, press D-pad right once.
5. Stop recording once the selection has moved.
6. Wait for **"Boot data NNN saved"** (about 40 s after power-on). Write NNN
   in the `boot` column of a `menu` row. If you miss it, wait 45 s anyway.
7. Power off from the menu, then go to step 1 for the next boot.

Game path, 10 boots (GBA via gpsp, the reference core, D10):

1. Launch the reference GBA game, play a few seconds, power off in the game.
   Wait 5 s.
2. Start recording as above, then power on. The game resumes by itself.
3. Stop recording once the game is moving.
4. Wait for **"Boot data NNN saved"** (it should show over the game; if it
   does not, wait 45 s). Write NNN in the `boot` column of a `game` row.
5. Power off in the game (this saves it again, so the next boot resumes
   too), then go to step 2 for the next boot.

Reading the videos: for each clip, write these times in seconds, as the
video player shows them (3 decimals), into the CSV. Leave a cell empty if it
does not apply.

| Column | Frame |
|---|---|
| `t_power_s` | The power switch is moved (T0) |
| `t_screen_on_s` | The screen first lights up (optional) |
| `t_menu_s` | The menu is fully drawn (menu path) |
| `t_response_s` | The selection has moved after your D-pad press (menu path) |
| `t_game_s` | First frame of moving gameplay (game path) |
| `notes` | Anything unusual (a stall, a wrong screen, a retry) |

After the round: MENU → MOUNT USB, copy the whole `starfling-boot` folder
and the CSV to the PC (for example `C:\Users\krayh\Downloads\`), and tell
the agent where they are. To give the agent adb again, create the `adb` file
(section 3).
