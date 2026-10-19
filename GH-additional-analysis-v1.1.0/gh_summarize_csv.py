#!/usr/bin/env python3
"""Summarize Greenberg-Hastings simulation CSV files without loading them into memory.

The script recursively scans files named like
``GH_size500x500_density15_refr34_run2.csv`` and produces one compact row
per input file.  It records late-time activity, extinction time, survival at
chosen observation times, and basic integrity checks.

The CSVs produced by Ander's runner label the first post-update state as
``Step = 0``.  Consequently, a checkpoint of 2000 updates corresponds to the
row whose Step value is 1999.
"""

import argparse
import csv
import math
import re
import sys
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_VERSION = "1.0.0"
REQUIRED_COLUMNS = (
    "Step",
    "Active_cells",
    "Refractory_cells",
    "Resting_cells",
)
FILENAME_RE = re.compile(
    r"GH_size(?P<width>\d+)x(?P<height>\d+)"
    r".*?density(?P<density>\d+(?:\.\d+)?)"
    r".*?refr(?P<refractory>\d+)"
    r"(?:.*?run(?P<run>\d+))?",
    re.IGNORECASE,
)


def parse_density(token):
    """Interpret integer filename tokens as percentages (15 -> 0.15)."""
    value = float(token)
    if "." not in token or value > 1.0:
        return value / 100.0
    return value


def parse_filename(path):
    match = FILENAME_RE.search(path.stem)
    if not match:
        return {
            "grid_width": "",
            "grid_height": "",
            "initial_density": "",
            "refractory_parameter": "",
            "run": "",
            "filename_parsed": 0,
        }

    groups = match.groupdict()
    return {
        "grid_width": int(groups["width"]),
        "grid_height": int(groups["height"]),
        "initial_density": parse_density(groups["density"]),
        "refractory_parameter": int(groups["refractory"]),
        "run": int(groups["run"]) if groups["run"] is not None else "",
        "filename_parsed": 1,
    }


def population_std(values, mean_value):
    if not values:
        return math.nan
    return math.sqrt(sum((value - mean_value) ** 2 for value in values) / len(values))


def summarize_file(path, root, late_window, checkpoints):
    metadata = parse_filename(path)
    expected_total = ""
    if metadata["filename_parsed"]:
        expected_total = metadata["grid_width"] * metadata["grid_height"]

    tail_active = deque(maxlen=late_window)
    row_count = 0
    first_step = None
    last_step = None
    previous_step = None
    step_discontinuities = 0
    first_recorded_active = None
    last_recorded_active = None
    last_active_step = None
    candidate_extinction_step = None
    zero_reactivation_events = 0
    total_mismatch_rows = 0
    min_total = None
    max_total = None
    checkpoint_active = {checkpoint: "" for checkpoint in checkpoints}

    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        missing = [column for column in REQUIRED_COLUMNS if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("missing columns: " + ", ".join(missing))

        for row in reader:
            step = int(row["Step"])
            active = int(row["Active_cells"])
            refractory = int(row["Refractory_cells"])
            resting = int(row["Resting_cells"])
            total = active + refractory + resting

            if first_step is None:
                first_step = step
                first_recorded_active = active
            if previous_step is not None and step != previous_step + 1:
                step_discontinuities += 1
            previous_step = step
            last_step = step
            last_recorded_active = active
            row_count += 1

            min_total = total if min_total is None else min(min_total, total)
            max_total = total if max_total is None else max(max_total, total)
            if expected_total != "" and total != expected_total:
                total_mismatch_rows += 1

            tail_active.append(active)

            if active > 0:
                last_active_step = step
                if candidate_extinction_step is not None:
                    zero_reactivation_events += 1
                    candidate_extinction_step = None
            elif candidate_extinction_step is None:
                candidate_extinction_step = step

            completed_updates = step + 1
            if completed_updates in checkpoint_active:
                checkpoint_active[completed_updates] = active

    if row_count == 0:
        raise ValueError("file contains no data rows")

    total_for_fraction = expected_total if expected_total != "" else max_total
    tail_mean_count = sum(tail_active) / len(tail_active)
    tail_std_count = population_std(tail_active, tail_mean_count)
    extinction_step = candidate_extinction_step if last_recorded_active == 0 else ""
    extinction_after_updates = extinction_step + 1 if extinction_step != "" else ""

    stat = path.stat()
    result = {
        "source_file": path.relative_to(root).as_posix(),
        "file_size_bytes": stat.st_size,
        "modified_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        **metadata,
        "rows": row_count,
        "first_step_label": first_step,
        "last_step_label": last_step,
        "updates_observed": last_step + 1,
        "first_recorded_active": first_recorded_active,
        "last_recorded_active": last_recorded_active,
        "last_active_step_label": last_active_step if last_active_step is not None else "",
        "extinction_step_label": extinction_step,
        "extinction_after_updates": extinction_after_updates,
        "survived_to_end": int(last_recorded_active > 0),
        "tail_all_zero": int(all(value == 0 for value in tail_active)),
        "late_window_rows": len(tail_active),
        "late_mean_active_count": tail_mean_count,
        "late_std_active_count": tail_std_count,
        "late_mean_active_fraction": tail_mean_count / total_for_fraction,
        "late_std_active_fraction": tail_std_count / total_for_fraction,
        "zero_reactivation_events": zero_reactivation_events,
        "step_discontinuities": step_discontinuities,
        "total_mismatch_rows": total_mismatch_rows,
        "minimum_total_cells": min_total,
        "maximum_total_cells": max_total,
    }

    for checkpoint in checkpoints:
        active = checkpoint_active[checkpoint]
        result[f"active_after_{checkpoint}_updates"] = active
        result[f"survived_after_{checkpoint}_updates"] = (
            int(active > 0) if active != "" else ""
        )

    return result


def build_fieldnames(checkpoints):
    fields = [
        "source_file",
        "file_size_bytes",
        "modified_utc",
        "filename_parsed",
        "grid_width",
        "grid_height",
        "initial_density",
        "refractory_parameter",
        "run",
        "rows",
        "first_step_label",
        "last_step_label",
        "updates_observed",
        "first_recorded_active",
        "last_recorded_active",
        "last_active_step_label",
        "extinction_step_label",
        "extinction_after_updates",
        "survived_to_end",
        "tail_all_zero",
        "late_window_rows",
        "late_mean_active_count",
        "late_std_active_count",
        "late_mean_active_fraction",
        "late_std_active_fraction",
        "zero_reactivation_events",
        "step_discontinuities",
        "total_mismatch_rows",
        "minimum_total_cells",
        "maximum_total_cells",
    ]
    for checkpoint in checkpoints:
        fields.extend(
            [
                f"active_after_{checkpoint}_updates",
                f"survived_after_{checkpoint}_updates",
            ]
        )
    return fields


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Create a compact audit summary of Greenberg-Hastings CSV simulations."
    )
    parser.add_argument("data_root", type=Path, help="Root folder containing the CSV files")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output summary CSV (default: DATA_ROOT/gh_simulation_summary.csv)",
    )
    parser.add_argument(
        "--late-window",
        type=int,
        default=100,
        help="Number of final rows used for late-time activity (default: 100)",
    )
    parser.add_argument(
        "--checkpoints",
        type=int,
        nargs="*",
        default=[1000, 2000, 5000, 10000],
        help="Observation times in completed updates (default: 1000 2000 5000 10000)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    root = args.data_root.expanduser().resolve()
    if not root.is_dir():
        print(f"Error: data folder does not exist: {root}", file=sys.stderr)
        return 2
    if args.late_window < 1:
        print("Error: --late-window must be positive", file=sys.stderr)
        return 2

    checkpoints = sorted(set(value for value in args.checkpoints if value > 0))
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else root / "gh_simulation_summary.csv"
    )
    errors_output = output.with_name(output.stem + "_errors.csv")

    excluded = {output.resolve(), errors_output.resolve()}
    files = sorted(
        path for path in root.rglob("*.csv") if path.resolve() not in excluded
    )
    if not files:
        print(f"No CSV files found under: {root}", file=sys.stderr)
        return 1

    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = build_fieldnames(checkpoints)
    error_rows = []
    processed = 0

    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for index, path in enumerate(files, start=1):
            try:
                writer.writerow(
                    summarize_file(path, root, args.late_window, checkpoints)
                )
                processed += 1
            except Exception as exc:  # Keep scanning and report every problematic file.
                error_rows.append(
                    {
                        "source_file": path.relative_to(root).as_posix(),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            if index % 100 == 0 or index == len(files):
                print(f"Scanned {index}/{len(files)} files...", flush=True)

    if error_rows:
        with errors_output.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=["source_file", "error"])
            writer.writeheader()
            writer.writerows(error_rows)

    print(f"Summary written to: {output}")
    print(f"Successfully summarized: {processed}/{len(files)} files")
    print(f"Script version: {SCRIPT_VERSION}")
    if error_rows:
        print(f"Files with errors: {len(error_rows)}; details: {errors_output}")
    return 0 if processed else 1


if __name__ == "__main__":
    raise SystemExit(main())
