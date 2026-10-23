#!/usr/bin/env python3
"""Turn StarFling boot data and K's video timings into timeline tables.

    tools/starfling/boot-report.py BOOT_DIR [--video CSV] [--out FILE]

BOOT_DIR is a copy of /mnt/starfling-boot from the device: one NNN/ folder
per boot, written by starfling-boot-collect (dmesg.txt, info.txt and,
optionally, retrofe.log and bootchart.tgz). CSV is K's video sheet,
docs/starfling/boot-timing-template.csv; its "boot" column names the NNN
folder that the on-screen "Boot data NNN saved" notification showed.

Every on-device time comes from the kernel log, so it is seconds since the
kernel's clock started, not since power-on. The bootloader, and the kernel
before its clock starts, are invisible on the device. On a menu boot the video
fills that gap: video time from power-on to the first menu frame, minus the
kernel's time at "menu first frame", is the pre-kernel time.

Output is Markdown: one timeline per boot, then per-path medians over the
boots that are valid timing samples (adb, usbnet and bootchart off).
Python 3 standard library only.
"""

import argparse
import csv
import re
import statistics
import sys
from pathlib import Path

DMESG_LINE = re.compile(r"^\[\s*(\d+\.\d+)\]\s(.*)$")
BOOTMARK_PREFIX = "bootmark: "

# Kernel messages worth a row in the timeline, as (substring, label)
KERNEL_EVENTS = [
    ("Freeing unused kernel memory", "kernel: init starts"),
    ("FAT-fs (mmcblk0p4)", "kernel: /mnt mounting"),
]

# The collector's own work is after the boot it measures
LAST_MARK = "collect start"

MENU_FRAME_MARK = "retrofe menu first frame"
MENU_INPUT_MARK = "retrofe menu accepts input"
GAME_MARK = "game exec"

# Measured on the RG Nano on 2026-10-23: one shell mark written to /dev/kmsg
SHELL_MARK_COST_MS = 0.25

FLAGS_THAT_INVALIDATE = ("adb", "usbnet", "bootchart")


def parse_info(path):
    info = {}
    if not path.exists():
        return info
    for line in path.read_text(errors="replace").splitlines():
        key, sep, value = line.partition("=")
        if sep:
            info[key.strip()] = value.strip().strip('"')
    return info


def parse_events(dmesg_path):
    """Return [(seconds, label)] in log order, up to the collector's mark.

    A label can repeat (RetroFE restarts after a game, an adb shell sources
    .profile); only the first occurrence is kept, which is the boot's. Font
    marks are the exception: one font can load several times in one start
    (once per colour), so repeats are numbered instead.
    """
    events = []
    seen = set()
    font_count = {}
    kernel_seen = set()
    for line in dmesg_path.read_text(errors="replace").splitlines():
        match = DMESG_LINE.match(line)
        if not match:
            continue
        seconds, text = float(match.group(1)), match.group(2)

        if text.startswith(BOOTMARK_PREFIX):
            label = text[len(BOOTMARK_PREFIX):].strip()
            if label == LAST_MARK:
                break
            if is_font_mark(label):
                key = step_key(label)
                font_count[key] = font_count.get(key, 0) + 1
                if font_count[key] > 1:
                    label = f"{key} #{font_count[key]}{label[len(key):]}"
            if label in seen:
                continue
            seen.add(label)
            events.append((seconds, label))
            continue

        for needle, label in KERNEL_EVENTS:
            if needle in text and label not in kernel_seen:
                kernel_seen.add(label)
                events.append((seconds, label))
    return events


FONT_DURATION = re.compile(r" took (\d+) ms$")


def step_key(label):
    """Label without a per-boot duration, so steps line up across boots."""
    return FONT_DURATION.sub("", label)


def is_font_mark(label):
    return label.startswith("retrofe font ")


def font_total_ms(events):
    total = 0
    for _, label in events:
        match = FONT_DURATION.search(label)
        if is_font_mark(label) and match:
            total += int(match.group(1))
    return total


def boot_path(events):
    return "game" if any(label == GAME_MARK for _, label in events) else "menu"


def invalid_reasons(info):
    return [flag for flag in FLAGS_THAT_INVALIDATE if info.get(flag) == "1"]


def mark_time(events, label):
    for seconds, name in events:
        if name == label:
            return seconds
    return None


def load_video(csv_path):
    """Return {boot id: row}, with time columns as floats or None."""
    rows = {}
    with open(csv_path, newline="") as handle:
        for row in csv.DictReader(line for line in handle if not line.startswith("#")):
            boot = (row.get("boot") or "").strip()
            if not boot:
                continue
            for key, value in list(row.items()):
                if key and key.startswith("t_"):
                    value = (value or "").strip()
                    row[key] = float(value) if value else None
            rows[boot.zfill(3)] = row
    return rows


def video_durations(row):
    """Seconds from power-on to each video event, or None where not read."""
    start = row.get("t_power_s")
    if start is None:
        return {}
    durations = {}
    for key in ("t_screen_on_s", "t_menu_s", "t_response_s", "t_game_s"):
        if row.get(key) is not None:
            durations[key[2:-2]] = row[key] - start
    return durations


def fmt_s(value):
    return "" if value is None else f"{value:.3f}"


def fmt_ms(value):
    return "" if value is None else f"{value * 1000:.0f}"


def boot_section(boot_id, info, events, video_row):
    out = []
    reasons = invalid_reasons(info)
    path = boot_path(events)
    status = "NOT a timing sample (" + ", ".join(f"{r} on" for r in reasons) + ")" if reasons else "timing sample"
    out.append(f"## Boot {boot_id} ({path} path, {status})\n")
    if info.get("NAME") or info.get("VERSION_ID"):
        out.append(f"Build: {info.get('NAME', '?')} {info.get('VERSION_ID', '?')}\n")

    out.append("| t (s) | step | step took (ms) |")
    out.append("|---:|---|---:|")
    timeline = [(0.0, "kernel: clock starts")] + events
    for index, (seconds, label) in enumerate(timeline):
        took = None
        if index + 1 < len(timeline):
            took = timeline[index + 1][0] - seconds
        out.append(f"| {fmt_s(seconds)} | {label} | {fmt_ms(took)} |")
    out.append("")

    shell_marks = sum(1 for _, label in events if not label.startswith("retrofe ") and not label.startswith("kernel:"))
    out.append(f"Fonts: {font_total_ms(events)} ms total. "
               f"Instrumentation estimate: {shell_marks} shell marks, "
               f"about {shell_marks * SHELL_MARK_COST_MS:.0f} ms.\n")

    if video_row:
        durations = video_durations(video_row)
        menu_frame = mark_time(events, MENU_FRAME_MARK)
        lines = [f"Video: {k} at {v:.3f} s after power-on" for k, v in durations.items()]
        if "menu" in durations and menu_frame is not None:
            pre_kernel = durations["menu"] - menu_frame
            lines.append(f"Pre-kernel (video menu - kernel '{MENU_FRAME_MARK}'): {pre_kernel:.3f} s")
        out.extend(f"- {line}" for line in lines)
        out.append("")
    return out


def summary_section(path, samples):
    """samples: [(boot id, events, video row or None)] of valid boots."""
    out = [f"## Medians, {path} path ({len(samples)} timing boots)\n"]

    # Step durations keyed by the step's starting event; the first boot's
    # order defines the row order, and later-only labels are appended.
    order = []
    starts = {}
    took = {}
    for _, events, _ in samples:
        timeline = [(0.0, "kernel: clock starts")] + events
        for index, (seconds, label) in enumerate(timeline):
            label = step_key(label)
            if label not in starts:
                order.append(label)
                starts[label] = []
                took[label] = []
            starts[label].append(seconds)
            if index + 1 < len(timeline):
                took[label].append(timeline[index + 1][0] - seconds)

    out.append("| step | median t (s) | median took (ms) | min-max took (ms) | n |")
    out.append("|---|---:|---:|---:|---:|")
    for label in order:
        durations = took[label]
        median_took = statistics.median(durations) if durations else None
        spread = f"{min(durations) * 1000:.0f}-{max(durations) * 1000:.0f}" if durations else ""
        out.append(f"| {label} | {fmt_s(statistics.median(starts[label]))} | "
                   f"{fmt_ms(median_took)} | {spread} | {len(starts[label])} |")
    out.append("")

    video_keys = {}
    pre_kernel = []
    for _, events, row in samples:
        if not row:
            continue
        durations = video_durations(row)
        for key, value in durations.items():
            video_keys.setdefault(key, []).append(value)
        menu_frame = mark_time(events, MENU_FRAME_MARK)
        if "menu" in durations and menu_frame is not None:
            pre_kernel.append(durations["menu"] - menu_frame)

    if video_keys or pre_kernel:
        out.append("| video measure | median (s) | min-max (s) | n |")
        out.append("|---|---:|---:|---:|")
        for key, values in video_keys.items():
            out.append(f"| power-on to {key} | {statistics.median(values):.3f} | "
                       f"{min(values):.3f}-{max(values):.3f} | {len(values)} |")
        if pre_kernel:
            out.append(f"| pre-kernel (video menu - kernel menu frame) | {statistics.median(pre_kernel):.3f} | "
                       f"{min(pre_kernel):.3f}-{max(pre_kernel):.3f} | {len(pre_kernel)} |")
        out.append("")
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("boot_dir", type=Path, help="copy of /mnt/starfling-boot")
    parser.add_argument("--video", type=Path, help="K's video CSV (boot-timing-template.csv)")
    parser.add_argument("--out", type=Path, help="write Markdown here instead of stdout")
    args = parser.parse_args()

    boot_dirs = sorted(d for d in args.boot_dir.iterdir() if d.is_dir() and (d / "dmesg.txt").exists())
    if not boot_dirs:
        sys.exit(f"no NNN/dmesg.txt folders under {args.boot_dir}")

    video = load_video(args.video) if args.video else {}
    missing = sorted(set(video) - {d.name for d in boot_dirs})
    if missing:
        print(f"warning: video rows with no boot folder: {', '.join(missing)}", file=sys.stderr)

    out = ["# StarFling boot report\n"]
    by_path = {}
    for boot in boot_dirs:
        info = parse_info(boot / "info.txt")
        events = parse_events(boot / "dmesg.txt")
        row = video.get(boot.name)
        if row and (row.get("path") or "").strip() not in ("", boot_path(events)):
            print(f"warning: boot {boot.name}: CSV says {row['path']} path, log says {boot_path(events)}",
                  file=sys.stderr)
        out.extend(boot_section(boot.name, info, events, row))
        if not invalid_reasons(info):
            by_path.setdefault(boot_path(events), []).append((boot.name, events, row))

    for path in sorted(by_path):
        out.extend(summary_section(path, by_path[path]))
    if not by_path:
        out.append("No valid timing boots: every boot had adb, usbnet or bootchart on.\n")

    text = "\n".join(out)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
