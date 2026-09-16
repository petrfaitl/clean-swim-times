#!/usr/bin/env python3
"""
clean_times.py - Universal Swim Entry Time Sanitizer and Normalizer.

Cleans and standardizes swim entry times corrupted by spreadsheet clock formatting (HH:MM:SS):
- Sprint times (< 1 min, 25m & 50m) -> SS.SS (e.g. 36.00, 29.37)
- Mid-distance times (1:00 to 9:59, 100m to 400m) -> M:SS.SS (e.g. 1:08.00, 6:00.00)
- Long-distance times (>= 10:00, 800m & 1500m) -> MM:SS.SS (e.g. 13:00.00, 26:00.00)
- Zero/No Time entries -> 0:00.00 or NT
"""

import argparse
import csv
import os
import re
import shutil
import sys
from typing import List, Dict, Any, Optional, Tuple

VALID_TIME_PATTERN = re.compile(
    r"^(\d{2}\.\d{2}|\d:[0-5]\d\.\d{2}|[1-5]\d:[0-5]\d\.\d{2}|0:00\.00|NT)$"
)

def parse_distance(event_name: str) -> int:
    """Extract race distance in meters from event string."""
    cleaned = event_name.replace(",", "")
    match = re.search(r'\b(25|50|100|200|400|800|1500)\s*(?:m\b|\b)', cleaned, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0

def normalize_time(event_name: str, raw_time: str) -> str:
    """
    Normalize raw swim time into standardized SS.SS, M:SS.SS, or MM:SS.SS format.
    """
    raw = raw_time.strip()
    if not raw:
        return ""
    if raw in ("00:00:00", "0:00.00", "00:00", "0:00", "0"):
        return "0:00.00"
    if raw.upper() in ("NT", "N/T", "NO TIME"):
        return "NT"

    dist = parse_distance(event_name)
    is_sprint_event = (dist in (25, 50)) or ("25m" in event_name.lower()) or ("50m" in event_name.lower())

    # Case 1: Already clean formatted times
    # SS.SS or SS.ss (e.g. 36.00, 29.37)
    if re.match(r'^\d{2}\.\d{2}$', raw) and (is_sprint_event or dist == 0):
        return raw
    # M:SS.SS (e.g. 1:08.00, 1:30.95)
    if re.match(r'^[1-9]:[0-5]\d\.\d{2}$', raw):
        return raw
    # MM:SS.SS (e.g. 13:00.00, 26:00.00)
    if re.match(r'^[1-5]\d:[0-5]\d\.\d{2}$', raw):
        return raw

    parts = raw.split(":")

    # Format 1: H:M:S (3 parts)
    if len(parts) == 3:
        h, m, s = parts[0].strip(), parts[1].strip(), parts[2].strip()

        # 00:00:SS -> SS.00
        if int(h) == 0 and int(m) == 0:
            if "." in s:
                sec_val = float(s)
                return f"{sec_val:05.2f}" if sec_val < 10 else f"{sec_val:.2f}"
            return f"{int(s):02d}.00"

        # Sprint event (25m / 50m)
        if is_sprint_event:
            # Slower 50m swims >= 1 minute (e.g. 00:01:03 -> 1:03.00)
            if int(h) == 0 and int(m) in (1, 2) and int(float(s)) < 60:
                sec = int(float(s))
                return f"{int(m)}:{sec:02d}.00"
            # Sprint with hundredths (e.g. 00:29:37 -> 29.37)
            if int(h) == 0 and s not in ("00", "0"):
                return f"{int(m):02d}.{s}"
            # Sprint with trailing zeros (e.g. 00:36:00 -> 36.00)
            if int(h) == 0 and s in ("00", "0"):
                return f"{int(m):02d}.00"

        # Distance event (100m+)
        else:
            # Fast sub-minute 100m swim (e.g. 00:55:00 -> 55.00)
            if int(h) == 0 and int(m) < 60 and s in ("00", "0") and int(m) >= 40 and dist == 100:
                return f"{int(m):02d}.00"
            # 00:MM:SS for distance (e.g. 00:01:08 -> 1:08.00, 00:13:00 -> 13:00.00)
            if int(h) == 0:
                tot_m = int(m)
                tot_s = int(float(s))
                if dist >= 800 or tot_m >= 10:
                    return f"{tot_m:02d}:{tot_s:02d}.00"
                else:
                    return f"{tot_m}:{tot_s:02d}.00"
            # HH:MM:00 -> M:SS.00 or MM:SS.00 (e.g. 01:45:00 -> 1:45.00)
            if s in ("00", "0"):
                tot_m = int(h)
                tot_s = int(m)
                if dist >= 800 or tot_m >= 10:
                    return f"{tot_m:02d}:{tot_s:02d}.00"
                else:
                    return f"{tot_m}:{tot_s:02d}.00"

    # Format 2: M:S or S:D (2 parts)
    elif len(parts) == 2:
        p1, p2 = parts[0].strip(), parts[1].strip()

        # Leading zero minute: 00:36 -> 36.00, 00:29.37 -> 29.37
        if int(p1) == 0:
            if "." in p2:
                sec_val = float(p2)
                return f"{sec_val:05.2f}" if sec_val < 10 else f"{sec_val:.2f}"
            return f"{int(p2):02d}.00"

        # Sprint event (25m / 50m)
        if is_sprint_event:
            # Entered as SS:DD (seconds:decimals with colon, e.g. 34:56 -> 34.56, 36:00 -> 36.00)
            if int(p1) >= 10:
                return f"{int(p1):02d}.{p2}"
            # Slow 50m swim >= 1 minute (e.g. 1:03 -> 1:03.00)
            else:
                return f"{int(p1)}:{int(p2):02d}.00"

        # Distance event (100m+)
        else:
            m = int(p1)
            if "." in p2:
                sec_parts = p2.split(".")
                sec = int(sec_parts[0])
                hund = sec_parts[1][:2].ljust(2, "0")
                if dist >= 800 or m >= 10:
                    return f"{m:02d}:{sec:02d}.{hund}"
                return f"{m}:{sec:02d}.{hund}"
            else:
                sec = int(p2)
                if dist >= 800 or m >= 10:
                    return f"{m:02d}:{sec:02d}.00"
                return f"{m}:{sec:02d}.00"

    # Format 3: Plain number or decimal (1 part)
    elif len(parts) == 1:
        # Long-distance whole minutes (e.g. 13 for 800 Free -> 13:00.00)
        if dist >= 800 and float(raw).is_integer() and 8 <= int(float(raw)) <= 60:
            return f"{int(float(raw)):02d}:00.00"

        # Decimal or whole seconds (e.g. 36.5 -> 36.50, 32 -> 32.00)
        if "." in raw:
            sec_parts = raw.split(".")
            s = int(sec_parts[0])
            hund = sec_parts[1][:2].ljust(2, "0")
            return f"{s:02d}.{hund}"
        else:
            val = int(raw)
            return f"{val:02d}.00"

    raise ValueError(f"Unrecognized time format: '{raw}' for event '{event_name}'")

def detect_columns(header: List[str]) -> List[Dict[str, Any]]:
    """
    Universally detect event and time columns across different CSV formats:
    1. Paired columns: Event N and Time N (or Time column preceded by Event column)
    2. Event-named columns: Columns whose header itself specifies a swim event (e.g. '50 Free')
    """
    columns = []

    # Strategy 1: Look for numbered pairs 'Event N' and 'Time N'
    numbered_events: Dict[str, int] = {}
    numbered_times: Dict[str, int] = {}
    for idx, col in enumerate(header):
        col_clean = col.strip()
        ev_match = re.match(r'^Event\s*#?(\d+)\b', col_clean, re.IGNORECASE)
        if ev_match:
            numbered_events[ev_match.group(1)] = idx
        t_match = re.match(r'^(?:Seed\s*Time|Entry\s*Time|Time)\s*#?(\d+)\b', col_clean, re.IGNORECASE)
        if t_match:
            numbered_times[t_match.group(1)] = idx

    common_nums = sorted(set(numbered_events.keys()) & set(numbered_times.keys()), key=lambda x: int(x))
    if common_nums:
        for num in common_nums:
            columns.append({
                "type": "paired",
                "event_col": numbered_events[num],
                "time_col": numbered_times[num],
                "static_event_name": None,
                "event_header": header[numbered_events[num]],
                "time_header": header[numbered_times[num]]
            })
        return columns

    # Strategy 2: Direct event-named headers (e.g. '50 Free', '100 Back', '400 Free', '1,500 Free')
    event_pattern = re.compile(
        r'^(?:Event\s*\d+\s*[-:]\s*)?(?:25|50|100|200|400|800|1500|1,500)\s*m?\s*(?:Free(?:style)?|Back(?:stroke)?|Breast(?:stroke)?|Fly|Butterfly|IM|Individual Medley|any stroke)\b',
        re.IGNORECASE
    )
    for idx, col in enumerate(header):
        col_clean = col.strip()
        if len(col_clean) > 40:
            continue
        if "nominated" in col_clean.lower():
            continue
        if event_pattern.search(col_clean):
            columns.append({
                "type": "header_event",
                "event_col": None,
                "time_col": idx,
                "static_event_name": col_clean,
                "event_header": col,
                "time_header": col
            })
    if columns:
        return columns

    # Strategy 3: Explicit Time headers (e.g. 'Time', 'Seed Time') preceded by 'Event' headers
    for idx, col in enumerate(header):
        col_clean = col.strip()
        if len(col_clean) > 40:
            continue
        if re.match(r'^(?:Seed\s*Time|Entry\s*Time|Time)\b', col_clean, re.IGNORECASE):
            ev_idx = idx - 1 if (idx > 0 and "event" in header[idx - 1].lower()) else None
            columns.append({
                "type": "paired" if ev_idx is not None else "time_only",
                "event_col": ev_idx,
                "time_col": idx,
                "static_event_name": None if ev_idx is not None else header[idx],
                "event_header": header[ev_idx] if ev_idx is not None else None,
                "time_header": header[idx]
            })

    return columns

def dry_run_csv(file_path: str, encoding: str = "utf-8-sig", verbose: bool = False) -> Dict[str, Any]:
    """Validate swim times in the input CSV without modifying the file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Input file not found: {file_path}")

    with open(file_path, "r", encoding=encoding) as f:
        reader = list(csv.reader(f))

    if not reader:
        print(f"File {file_path} is empty.")
        return {"rows": 0, "times_checked": 0, "errors": 0}

    header = reader[0]
    col_mapping = detect_columns(header)
    if not col_mapping:
        raise ValueError(f"Could not automatically detect any event/time columns in {file_path}")

    print(f"Input file: {file_path}")
    print(f"Total rows (including header): {len(reader)}")
    print(f"Detected event/time columns: {len(col_mapping)}")

    stats = {
        "rows": len(reader) - 1,
        "times_checked": 0,
        "sprints": 0,
        "mid_distance": 0,
        "long_distance": 0,
        "zero_or_nt": 0,
        "errors": 0
    }

    # Identify swimmer name columns if present for friendly logging
    name_cols = [i for i, h in enumerate(header) if any(k in h.lower() for k in ["name", "swimmer", "athlete"])]

    for row_idx, row in enumerate(reader[1:], start=2):
        row_label = f"Row {row_idx}"
        if name_cols:
            names = [row[c].strip() for c in name_cols if c < len(row) and row[c].strip()]
            if names:
                row_label = f"Row {row_idx} ({' '.join(names)})"

        for mapping in col_mapping:
            t_col = mapping["time_col"]
            if t_col >= len(row):
                continue
            raw_t = row[t_col].strip()
            if not raw_t:
                continue

            # Determine event name
            if mapping["type"] == "paired" and mapping["event_col"] is not None and mapping["event_col"] < len(row):
                ev_name = row[mapping["event_col"]].strip()
            else:
                ev_name = mapping["static_event_name"] or "Swim Event"

            try:
                cleaned = normalize_time(ev_name, raw_t)
                if not VALID_TIME_PATTERN.match(cleaned):
                    print(f"WARNING: {row_label} {ev_name}: '{raw_t}' -> '{cleaned}' does not match target pattern")
                    stats["errors"] += 1
                else:
                    stats["times_checked"] += 1
                    if cleaned in ("0:00.00", "NT"):
                        stats["zero_or_nt"] += 1
                    elif ":" not in cleaned:
                        stats["sprints"] += 1
                    elif cleaned.startswith(("1:", "2:", "3:", "4:", "5:", "6:", "7:", "8:", "9:")):
                        stats["mid_distance"] += 1
                    else:
                        stats["long_distance"] += 1

                if verbose:
                    print(f"  {row_label} | {ev_name}: '{raw_t}' -> '{cleaned}'")
            except Exception as e:
                print(f"ERROR: {row_label} | {ev_name}: Failed to normalize '{raw_t}': {e}")
                stats["errors"] += 1

    print("\nDry Run Validation Summary:")
    print(f"  Swimmer rows:          {stats['rows']}")
    print(f"  Valid times cleaned:   {stats['times_checked']}")
    print(f"    Sprints (SS.SS):     {stats['sprints']}")
    print(f"    Mid-dist (M:SS.SS):  {stats['mid_distance']}")
    print(f"    Long-dist (MM:SS.SS):{stats['long_distance']}")
    print(f"    Zero / NT:           {stats['zero_or_nt']}")
    print(f"  Errors / Warnings:     {stats['errors']}")

    return stats

def clean_csv(
    input_path: str,
    output_path: Optional[str] = None,
    encoding: str = "utf-8-sig",
    backup: bool = False,
    verbose: bool = False
) -> str:
    """Clean and standardize swim times in a CSV file and save the result."""
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    if not output_path:
        base, ext = os.path.splitext(input_path)
        output_path = f"{base}-cleaned{ext}"

    with open(input_path, "r", encoding=encoding, newline="") as f:
        reader = list(csv.reader(f))

    if not reader:
        print(f"Input file {input_path} is empty.")
        return output_path

    header = reader[0]
    col_mapping = detect_columns(header)
    if not col_mapping:
        raise ValueError(f"Could not automatically detect any event/time columns in {input_path}")

    cleaned_rows = [header]
    total_cleaned = 0

    for row_idx, row in enumerate(reader[1:], start=2):
        new_row = list(row)
        for mapping in col_mapping:
            t_col = mapping["time_col"]
            if t_col >= len(new_row):
                continue
            raw_t = new_row[t_col].strip()
            if not raw_t:
                continue

            if mapping["type"] == "paired" and mapping["event_col"] is not None and mapping["event_col"] < len(new_row):
                ev_name = new_row[mapping["event_col"]].strip()
            else:
                ev_name = mapping["static_event_name"] or "Swim Event"

            cleaned_t = normalize_time(ev_name, raw_t)
            new_row[t_col] = cleaned_t
            total_cleaned += 1
            if verbose:
                print(f"  Row {row_idx} {ev_name}: '{raw_t}' -> '{cleaned_t}'")

        cleaned_rows.append(new_row)

    if backup and os.path.abspath(input_path) == os.path.abspath(output_path):
        backup_path = f"{input_path}.bak"
        shutil.copyfile(input_path, backup_path)
        print(f"Backup created at: {backup_path}")

    with open(output_path, "w", encoding=encoding, newline="") as f:
        writer = csv.writer(f)
        writer.writerows(cleaned_rows)

    print(f"Successfully cleaned {total_cleaned} entry times across {len(cleaned_rows) - 1} rows.")
    print(f"Saved cleaned CSV to: {output_path}")
    return output_path

def test_normalization():
    """Run comprehensive unit tests validating normalization logic."""
    print("Running normalization unit tests...")

    # Scenario 1: Sprint Times (00:00:SS to SS.00)
    assert normalize_time("50m Freestyle", "00:00:32") == "32.00"
    assert normalize_time("25m Butterfly", "00:00:13") == "13.00"

    # Scenario 2: Sprint Times with Trailing Zeros (00:MM:00 to SS.00)
    assert normalize_time("50m Butterfly", "00:35:00") == "35.00"
    assert normalize_time("50m Backstroke", "00:42:00") == "42.00"
    assert normalize_time("50m Backstroke", "00:36:00") == "36.00"
    assert normalize_time("50m Breaststroke", "00:58:00") == "58.00"

    # Scenario 3: Sprint Times with Hundredths (00:SS:ss to SS.ss)
    assert normalize_time("50m Freestyle", "00:29:37") == "29.37"
    assert normalize_time("25m Butterfly", "00:14:59") == "14.59"
    assert normalize_time("50m Backstroke", "00:44:05") == "44.05"
    assert normalize_time("50m Backstroke", "00:35:50") == "35.50"
    assert normalize_time("25m Freestyle", "00:13:54") == "13.54"

    # Scenario 4: Middle-Distance Times Under 10 Min (00:MM:SS to M:SS.00)
    assert normalize_time("100m Freestyle", "00:01:08") == "1:08.00"
    assert normalize_time("400m Freestyle", "00:06:00") == "6:00.00"
    assert normalize_time("200m Freestyle", "00:02:59") == "2:59.00"

    # Scenario 5: Middle-Distance Times with Hours (HH:MM:00 to M:SS.00)
    assert normalize_time("100m Individual Medley", "01:45:00") == "1:45.00"
    assert normalize_time("200m Freestyle", "02:40:00") == "2:40.00"
    assert normalize_time("400m Freestyle", "04:40:00") == "4:40.00"
    assert normalize_time("100m Backstroke", "01:50:00") == "1:50.00"
    assert normalize_time("100m Freestyle", "01:30:00") == "1:30.00"
    assert normalize_time("200m Freestyle", "03:18:00") == "3:18.00"

    # Scenario 6: Long-Distance Times Over 9:59 (00:MM:SS to MM:SS.SS)
    assert normalize_time("800m Freestyle", "00:13:00") == "13:00.00"
    assert normalize_time("1500m Freestyle", "00:26:00") == "26:00.00"
    assert normalize_time("1500m Freestyle", "00:19:07") == "19:07.00"
    assert normalize_time("400m Freestyle", "00:13:00") == "13:00.00"

    # Scenario 7: Fast 100m Sprint (< 1 min)
    assert normalize_time("100m Freestyle", "00:55:00") == "55.00"

    # Scenario 8: Already Cleaned Times
    assert normalize_time("50m Freestyle", "36.00") == "36.00"
    assert normalize_time("50m Freestyle", "29.37") == "29.37"
    assert normalize_time("100m Freestyle", "1:08.00") == "1:08.00"
    assert normalize_time("800m Freestyle", "13:00.00") == "13:00.00"

    # Scenario 9: 2-Part Times (M:SS and SS:DD)
    assert normalize_time("100m Backstroke", "1:18") == "1:18.00"
    assert normalize_time("50m Freestyle", "34:56") == "34.56"
    assert normalize_time("50m Freestyle", "00:36") == "36.00"

    # Scenario 10: 1-Part Times
    assert normalize_time("800 Free", "13") == "13:00.00"
    assert normalize_time("50m Freestyle", "32") == "32.00"
    assert normalize_time("25m Freestyle", "14.5") == "14.50"

    # Scenario 11: Zero / No Time Entries
    assert normalize_time("100m Backstroke", "00:00:00") == "0:00.00"
    assert normalize_time("50m Freestyle", "NT") == "NT"
    assert normalize_time("50m Freestyle", "0:00.00") == "0:00.00"

    # Scenario 12: 50m Swims >= 1 Minute
    assert normalize_time("50m Freestyle", "00:01:03") == "1:03.00"
    assert normalize_time("50m Breaststroke", "00:01:31") == "1:31.00"
    assert normalize_time("50m Backstroke", "00:01:13") == "1:13.00"
    assert normalize_time("50m Freestyle", "00:01:10") == "1:10.00"
    assert normalize_time("50m Freestyle", "00:01:00") == "1:00.00"
    assert normalize_time("50m Butterfly", "00:01:05") == "1:05.00"
    assert normalize_time("50m Breaststroke", "00:01:10") == "1:10.00"
    assert normalize_time("50m Breaststroke", "00:01:00") == "1:00.00"
    assert normalize_time("50m Breaststroke", "00:01:05") == "1:05.00"
    assert normalize_time("50m Backstroke", "00:01:20") == "1:20.00"
    assert normalize_time("50m Butterfly", "00:01:00") == "1:00.00"
    assert normalize_time("50m Breaststroke", "00:01:20") == "1:20.00"

    print("All unit tests passed successfully!")

def parse_args():
    parser = argparse.ArgumentParser(
        description="Clean and standardize swim meet entry times in CSV files."
    )
    parser.add_argument(
        "-i", "--input", "--input-file",
        dest="input_file",
        default="Masters Spring Fling 2026 - INDIVIDUAL_EVENTS_TEMPLATE.csv",
        help="Path to input CSV file (default: %(default)s)"
    )
    parser.add_argument(
        "-o", "--output", "--output-file",
        dest="output_file",
        default=None,
        help="Path to output CSV file (default: <input>-cleaned.csv)"
    )
    parser.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite the input file directly"
    )
    parser.add_argument(
        "-d", "--dry-run",
        action="store_true",
        help="Validate and preview normalization without writing changes"
    )
    parser.add_argument(
        "-t", "--test",
        action="store_true",
        help="Run normalization unit tests"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print detailed row-by-row normalization actions"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a .bak backup file when modifying or writing in-place"
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="File encoding for reading/writing CSV (default: utf-8-sig)"
    )
    return parser.parse_args()

def main():
    args = parse_args()

    if args.test:
        test_normalization()
        return

    input_path = args.input_file
    if not os.path.exists(input_path):
        print(f"Error: Input file '{input_path}' not found.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        dry_run_csv(input_path, encoding=args.encoding, verbose=args.verbose)
        return

    output_path = args.output_file
    if args.in_place:
        output_path = input_path

    clean_csv(
        input_path=input_path,
        output_path=output_path,
        encoding=args.encoding,
        backup=args.backup,
        verbose=args.verbose
    )

if __name__ == "__main__":
    main()
