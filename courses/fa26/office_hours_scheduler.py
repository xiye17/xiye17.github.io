#!/usr/bin/env python3
"""Build and validate the CMPUT 267 Fall 2026 office-hour schedule.

The availability below was converted from the TAs' When2meet responses and
manually confirmed adjustments into complete one-hour blocks. Times use the
course's Edmonton local time.

Examples:
    python3 office_hours_scheduler.py
    python3 office_hours_scheduler.py --show-availability
    python3 office_hours_scheduler.py --find --block "Ho Leong (Mike) Luo=Fri 14"
    python3 office_hours_scheduler.py --set "Ho Leong (Mike) Luo=Fri 15"

The default output is tab-separated so it can be pasted into Google Sheets.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterable, Mapping


DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri")
HOURS = tuple(range(9, 17))
WHEN2MEET_URL = "https://www.when2meet.com/?38160674-FBvOy"
TIMEZONE = "America/Edmonton"

Slot = tuple[str, int]


# A slot ("Mon", 9) means the TA is available for the full 9:00-10:00 hour.
TA_AVAILABILITY: dict[str, tuple[Slot, ...]] = {
    "Aditi Vidyarthi": (
        ("Mon", 11), ("Mon", 13), ("Mon", 15),
        ("Tue", 10), ("Tue", 11),
        ("Wed", 11), ("Wed", 15),
        ("Thu", 10), ("Thu", 11),
    ),
    "Ammaar Mohammed": (
        ("Mon", 14),
        ("Tue", 9), ("Tue", 10), ("Tue", 14),
        ("Thu", 9), ("Thu", 10), ("Thu", 14),
        ("Fri", 16),
    ),
    "Gábor Mihucz": (
        ("Tue", 15),
        ("Wed", 16),
        ("Thu", 15),
    ),
    "Jiajing (Jessica) Chen": (
        ("Mon", 9), ("Mon", 10), ("Mon", 11),
        ("Tue", 9), ("Tue", 10), ("Tue", 14), ("Tue", 15),
        ("Wed", 9), ("Wed", 10), ("Wed", 11),
        ("Thu", 9), ("Thu", 10), ("Thu", 14), ("Thu", 15),
    ),
    "Kaining Yang": (
        ("Tue", 10),
    ),
    "Ho Leong (Mike) Luo": (
        ("Mon", 9), ("Mon", 10), ("Mon", 13), ("Mon", 14),
        ("Tue", 9), ("Tue", 10), ("Tue", 14),
        ("Wed", 9), ("Wed", 10), ("Wed", 13), ("Wed", 14),
        ("Thu", 9), ("Thu", 10), ("Thu", 14),
        ("Fri", 9), ("Fri", 10), ("Fri", 11), ("Fri", 12),
        ("Fri", 13), ("Fri", 14), ("Fri", 15), ("Fri", 16),
    ),
    "Quang Hieu Pham": (
        ("Mon", 10), ("Mon", 11), ("Mon", 12), ("Mon", 13),
        ("Tue", 10), ("Tue", 11), ("Tue", 12), ("Tue", 13),
        ("Wed", 10), ("Wed", 11), ("Wed", 12), ("Wed", 13),
        ("Thu", 10), ("Thu", 11), ("Thu", 12), ("Thu", 13),
        ("Fri", 10), ("Fri", 11), ("Fri", 12), ("Fri", 13),
    ),
    "Songtao Wang": (
        ("Thu", 10), ("Thu", 11), ("Thu", 12), ("Thu", 16),
        ("Fri", 10), ("Fri", 11), ("Fri", 12), ("Fri", 13),
        ("Fri", 14), ("Fri", 15), ("Fri", 16),
    ),
    "Thuy Duong Nguyen": (
        ("Tue", 10), ("Tue", 11), ("Tue", 12), ("Tue", 13),
        ("Thu", 10), ("Thu", 11), ("Thu", 12), ("Thu", 13),
        ("Fri", 10), ("Fri", 11), ("Fri", 12), ("Fri", 13),
    ),
    # Connor was added during the manual scheduling adjustment.
    "Connor Mitchell": (
        ("Wed", 13),
    ),
}

INSTRUCTOR = "Xi Ye"
INSTRUCTOR_SLOT: Slot = ("Tue", 14)

# The schedule manually adjusted on 2026-08-31.
DEFAULT_SCHEDULE: dict[str, Slot] = {
    "Jiajing (Jessica) Chen": ("Mon", 10),
    "Aditi Vidyarthi": ("Mon", 13),
    "Kaining Yang": ("Tue", 10),
    INSTRUCTOR: INSTRUCTOR_SLOT,
    "Quang Hieu Pham": ("Wed", 11),
    "Connor Mitchell": ("Wed", 13),
    "Gábor Mihucz": ("Wed", 16),
    "Ammaar Mohammed": ("Thu", 9),
    "Songtao Wang": ("Thu", 16),
    "Thuy Duong Nguyen": ("Fri", 10),
    "Ho Leong (Mike) Luo": ("Fri", 14),
}


def period(hour: int) -> str:
    """Return a compact 12-hour label for a one-hour slot."""
    def clock(value: int) -> str:
        if value == 12:
            return "12:00"
        if value > 12:
            return f"{value - 12}:00"
        return f"{value}:00"

    return f"{clock(hour)}-{clock(hour + 1)}"


def slot_label(slot: Slot) -> str:
    day, hour = slot
    return f"{day} {period(hour)}"


def is_morning(slot: Slot) -> bool:
    return slot[1] < 12


def validate_schedule(schedule: Mapping[str, Slot]) -> list[str]:
    """Return all violations of the office-hour scheduling constraints."""
    errors: list[str] = []
    expected_people = set(TA_AVAILABILITY) | {INSTRUCTOR}
    actual_people = set(schedule)

    missing = sorted(expected_people - actual_people)
    extra = sorted(actual_people - expected_people)
    if missing:
        errors.append(f"Missing assignments: {', '.join(missing)}")
    if extra:
        errors.append(f"Unknown people: {', '.join(extra)}")

    if schedule.get(INSTRUCTOR) != INSTRUCTOR_SLOT:
        errors.append(
            f"{INSTRUCTOR}'s office hour must remain {slot_label(INSTRUCTOR_SLOT)}"
        )

    for ta, allowed_slots in TA_AVAILABILITY.items():
        if ta in schedule and schedule[ta] not in allowed_slots:
            errors.append(
                f"{ta} is not available for the full hour at "
                f"{slot_label(schedule[ta])}"
            )

    occupied: dict[Slot, list[str]] = {}
    for person, slot in schedule.items():
        occupied.setdefault(slot, []).append(person)
    for slot, people in occupied.items():
        if len(people) > 1:
            errors.append(
                f"Overlapping assignments at {slot_label(slot)}: {', '.join(people)}"
            )

    for day in DAYS:
        day_slots = [slot for slot in schedule.values() if slot[0] == day]
        morning_count = sum(is_morning(slot) for slot in day_slots)
        afternoon_count = len(day_slots) - morning_count
        if morning_count < 1 or afternoon_count < 1:
            errors.append(
                f"{day} must have at least 1 morning and 1 afternoon office hour"
            )

    return errors


def parse_assignment(value: str) -> tuple[str, Slot]:
    """Parse 'Name=Mon 9' from a command-line option."""
    try:
        name, raw_slot = value.rsplit("=", 1)
        day, raw_hour = raw_slot.split()
        hour = int(raw_hour.split(":", 1)[0])
    except (ValueError, TypeError) as error:
        raise argparse.ArgumentTypeError(
            f"Expected 'Name=Mon 9', received {value!r}"
        ) from error

    name = name.strip()
    if name not in TA_AVAILABILITY and name != INSTRUCTOR:
        raise argparse.ArgumentTypeError(f"Unknown person: {name}")
    if day not in DAYS or hour not in HOURS:
        raise argparse.ArgumentTypeError(f"Invalid slot: {raw_slot!r}")
    return name, (day, hour)


def find_schedule(
    fixed: Mapping[str, Slot] | None = None,
    blocked: Iterable[tuple[str, Slot]] = (),
) -> dict[str, Slot] | None:
    """Find a schedule satisfying all distribution and availability rules."""
    fixed_schedule = {INSTRUCTOR: INSTRUCTOR_SLOT}
    fixed_schedule.update(fixed or {})
    blocked_set = set(blocked)

    for person, slot in fixed_schedule.items():
        if (person, slot) in blocked_set:
            return None
        if person in TA_AVAILABILITY and slot not in TA_AVAILABILITY[person]:
            return None

    if len(set(fixed_schedule.values())) != len(fixed_schedule):
        return None

    people = [ta for ta in TA_AVAILABILITY if ta not in fixed_schedule]
    schedule = dict(fixed_schedule)
    occupied = set(schedule.values())

    def slot_fits(slot: Slot) -> bool:
        if slot in occupied:
            return False
        day, _ = slot
        same_day = [current for current in schedule.values() if current[0] == day]
        if len(same_day) >= 3:
            return False
        same_period_count = sum(
            is_morning(current) == is_morning(slot) for current in same_day
        )
        if same_period_count >= 2:
            return False
        return True

    def candidates(ta: str) -> list[Slot]:
        available = [
            slot
            for slot in TA_AVAILABILITY[ta]
            if (ta, slot) not in blocked_set and slot_fits(slot)
        ]
        preferred = DEFAULT_SCHEDULE.get(ta)
        return sorted(
            available,
            key=lambda slot: (
                slot != preferred,
                DAYS.index(slot[0]),
                slot[1],
            ),
        )

    def search(remaining: list[str]) -> bool:
        if not remaining:
            return not validate_schedule(schedule)

        ta = min(remaining, key=lambda person: len(candidates(person)))
        next_remaining = [person for person in remaining if person != ta]
        for slot in candidates(ta):
            schedule[ta] = slot
            occupied.add(slot)
            if search(next_remaining):
                return True
            occupied.remove(slot)
            del schedule[ta]
        return False

    return dict(schedule) if search(people) else None


def schedule_tsv(schedule: Mapping[str, Slot]) -> str:
    by_slot = {slot: person for person, slot in schedule.items()}
    lines = ["Time\t" + "\t".join(DAYS)]
    for hour in HOURS:
        row = [period(hour)]
        row.extend(by_slot.get((day, hour), "") for day in DAYS)
        lines.append("\t".join(row))
    return "\n".join(lines)


def availability_tsv() -> str:
    lines = ["TA\tAvailable one-hour blocks"]
    for ta, slots in TA_AVAILABILITY.items():
        lines.append(f"{ta}\t" + ", ".join(slot_label(slot) for slot in slots))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--show-availability",
        action="store_true",
        help="print every TA's valid one-hour blocks instead of a schedule",
    )
    parser.add_argument(
        "--find",
        action="store_true",
        help="search for a valid schedule instead of using the saved schedule",
    )
    parser.add_argument(
        "--set",
        dest="fixed",
        action="append",
        default=[],
        type=parse_assignment,
        metavar='"NAME=DAY HOUR"',
        help="set an assignment; repeat for multiple people",
    )
    parser.add_argument(
        "--block",
        action="append",
        default=[],
        type=parse_assignment,
        metavar='"NAME=DAY HOUR"',
        help="exclude an assignment while using --find; repeat as needed",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.show_availability:
        print(availability_tsv())
        return 0

    fixed = dict(args.fixed)
    if args.find:
        schedule = find_schedule(fixed=fixed, blocked=args.block)
        if schedule is None:
            print("No schedule satisfies the requested constraints.", file=sys.stderr)
            return 1
    else:
        if args.block:
            print("--block requires --find", file=sys.stderr)
            return 2
        schedule = dict(DEFAULT_SCHEDULE)
        schedule.update(fixed)

    errors = validate_schedule(schedule)
    if errors:
        print("Schedule is invalid:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(schedule_tsv(schedule))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
