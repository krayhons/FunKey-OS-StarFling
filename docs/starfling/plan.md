# StarFling — Roadmap and Model Plan

StarFling is a FunKey OS fork for the **Anbernic RG Nano only**. It is based on
[L-K-M/FunKey-OS-Starling](https://github.com/L-K-M/FunKey-OS-Starling), which
is a fork of the `rg_nano` branch of
[DrUm78/FunKey-OS](https://github.com/DrUm78/FunKey-OS/tree/rg_nano), which is
a fork of [FunKey-Project/FunKey-OS](https://github.com/FunKey-Project/FunKey-OS).

Repo: https://github.com/krayhons/FunKey-OS-StarFling (default branch `master`,
unmodified fork of Starling 3.1.3 at the start of Phase 0).

## How these plan files work

- `plan.md` (this file) is the roadmap: phases, decisions, guardrails, and the
  model table. Every chat reads it.
- Each phase gets its own brief: `PHASE-1-BOOT.md`, then `PHASE-2-<name>.md`,
  and so on. A chat for a phase reads `plan.md` plus only its own phase file.
  Emulator-core phases get one file and one chat per core.
- Put both in the repo under `docs/starfling/` and add one line to `CLAUDE.md`
  pointing at them, so Claude Code loads them at the start of each session.
- At the end of every chat (or at about 30–40% context left), the agent writes
  `docs/starfling/handoff/<phase>-<date>.md` using the template at the bottom
  of this file.

## Decisions so far

| # | Decision | Source |
|---|---|---|
| D1 | Target device: RG Nano only. Other console branches are out of scope. | K |
| D2 | Phase 1 goal: power-on to interactive menu in **≤ 3.0 s**, and power-on to gameplay on resume in **≤ 3.0 s** (baseline about 6 s on drum86). | K |
| D3 | Boot behaviour stays as upstream: menu if powered off in the menu, the same game if powered off in a game. This is FunKey's existing Instant Play; Phase 1 must keep it. | K |
| D4 | Keep RetroFE as the frontend in Phase 1. A lighter custom launcher is a candidate for a later phase. | K |
| D5 | Build host: WSL2 (Ubuntu 22.04 distro, repo on the WSL ext4 filesystem, not `/mnt/c`). | K |
| D6 | Coding agent: Claude Code. Device in the loop through adb over USB (usbipd-win), with K doing power cycles and phone-video timing. Serial is optional (see Phase 1 brief, "Measurement levels"). | K / plan |
| D7 | Keep `.fwu` update compatibility and the `FunKey-` filename prefix (the installed firmware globs `/mnt/FunKey-*.fwu`). | plan |
| D8 | Keep Recovery (`p1`) and the FN+START recovery entry working at all times. | plan |
| D9 | **USB-C audio is required** (the RG Nano has no 3.5 mm jack). Keep it, but take it off the boot critical path: deferred loading, smarter detection, event-driven switching (task 1.5a). | K |
| D10 | Reference core for the resume-to-game target: **GBA (gpsp)**. | K |
| D11 | Plan approved 2026-10-22. Next step: Phase 0 in a new Claude Code chat. | K |

## Guardrails for every phase

1. **Measure before and after every change.** No change merges without a
   before/after boot-timing record (see the Phase 1 brief for the method).
2. **One concern per commit.** Each commit is revertible on its own.
3. **Never regress the safety net:** Recovery boot, `.fwu` update over USB,
   Instant Play save/resume, Favorites, Recently Played, volume and
   brightness restore, low-battery shutdown, USB-C audio.
4. **The SD card is the boot device, so the device is effectively unbrickable.**
   Worst case is reflashing the card from Windows. Keep a known-good card.
5. **Stay readable against upstream.** Prefer new files and small patches over
   rewrites of upstream scripts. Record every intentional divergence in
   `docs/starfling/DIVERGENCE.md`.
6. **One subagent at a time.** The agent asks K before spawning more than
   one, and prefers doing work inline.
7. **No code outside the active phase's scope.** New ideas go into the phase
   file's backlog section.

## Phases

| Phase | Name | Chat(s) | Outcome |
|---|---|---|---|
| 0 | Fork setup and dev loop | 1 | StarFling builds in WSL2, boots on K's RG Nano, adb dev loop works, docs rebranded |
| 1 | Boot-time optimization | 1–3 | Menu ≤ 3.0 s, resume-to-game ≤ 3.0 s, no regressions |
| 2..n | Emulator cores (one per core) | 1 each | Per-core startup, savestate load, and performance; brief written at the start of each |
| later | Lighter launcher (optional) | 1–2 | Only if RetroFE remains the bottleneck after Phase 1 |
| later | Experimental fast-boot (optional) | 1 | U-Boot Falcon mode or a hibernation snapshot, only if Phase 1 misses target |

Phase 0 is short and sits inside the first Phase 1 chat if that is easier; it
is listed separately because every later phase depends on it.

### Phase 0 — Fork setup and dev loop (summary)

- 0.1 Set up WSL2 Ubuntu 22.04, install the README package list, clone to `~/`,
  `make all` (skip `make sdk`; it is only for publishing a toolchain).
- 0.2 Flash the unmodified Starling 3.1.3 image to a spare card and confirm it
  boots on K's RG Nano. **Starling's own README says nothing since 3.0.0
  has run on hardware**, so this is a real test, not a formality.
- 0.3 Rebrand: version string, `CHANGELOG.md` heading scheme
  (`## StarFling-X.Y.Z`), artifact names `FunKey-sdcard-StarFling-*-RG_Nano.img`
  (keep the `FunKey-` prefix), README header. Trim Starling-specific CI that
  K does not use (the GLM/Z.ai review workflow, PR-babysitting rules in
  `CLAUDE.md`).
- 0.4 Dev loop: enable adb on the device (`touch /mnt/adb`), attach it to WSL2
  with usbipd-win, confirm `adb shell`, `adb push`, `rw`/`ro`. Document the
  loop in `docs/starfling/DEVLOOP.md`.

## Model and task table

Models are Claude Code models. "Effort" is the reasoning effort to set.
"Size" is the expected task size (S < 1 h of agent time, M a few hours, L most
of a chat). Pick the cheapest row that fits; escalate only if the cheaper
model gets stuck twice.

| ID | Task | Model | Effort | Size | Why this model |
|---|---|---|---|---|---|
| 0.1 | WSL2 build setup, first build, fix build breaks | Sonnet | medium | M | Mostly following instructions and reading build logs |
| 0.2 | Verify stock Starling on hardware (K does the flashing) | Haiku | low | S | Checklist only |
| 0.3 | Rebrand version strings, artifact names, CHANGELOG, README | Haiku | low | S | Mechanical edits |
| 0.4 | adb dev loop and `DEVLOOP.md` | Sonnet | low | S | Small scripts and docs |
| 1.1 | Boot instrumentation (boot-mark tool, bootchart, RetroFE timestamps, log collector) | Sonnet | medium | M | Well-specified scripting |
| 1.2 | Baseline measurement and bottleneck report | Opus | high | M | Judgement: reading timelines and ranking levers |
| 1.3 | Userspace init restructure (fast path, deferred services, direct frontend launch) | Sonnet | high | M | Shell work with many regressions to guard |
| 1.4 | RetroFE startup profiling and fixes (lazy font, scan cache, splash) | Opus (design) then Sonnet (implement) | high / medium | L | C++ patch series against a pinned tag; design needs care |
| 1.5 | Kernel trim and cmdline tuning | Opus | high | M | Driver and device-tree dependencies; easy to break hardware |
| 1.5a | USB-C audio off the critical path (deferred modules, event-driven card switch, resume-path exception) | Opus (design) then Sonnet (implement) | high / medium | M | Hotplug and ALSA edge cases; easy to lose audio silently |
| 1.6 | U-Boot bootcmd and config tuning | Opus | high | M | Bootloader risk; must keep recovery entry |
| 1.7 | Instant Play resume path (game-start ordering) | Sonnet | medium | S | Ordering change in existing scripts |
| 1.8 | Regression pass and release notes | Sonnet (tests), Haiku (notes) | medium / low | M | Checklist execution, then prose |
| 1.9 | (Gated) experimental levers: squashfs root, Falcon mode, snapshot resume | Opus | high | L | Only if 1.3–1.7 miss target; K approves first |
| 2.x | Emulator core N (one chat each) | Sonnet; Opus for the plan of each core | medium / high | M–L | Plan written at the start of each core chat |

## Handoff template

```
# Handoff: <phase> — <date>
## Done (with commit hashes)
## Measurements (table: change, menu ms, game ms, n boots)
## In progress / exact next step
## Decisions made this chat (and why)
## Open questions for K
## Files touched
```
