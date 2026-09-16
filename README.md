# Swim Entry Time Sanitizer (`clean_times.py`)

A universal Python utility designed to clean and standardize swim meet entry times in CSV files. It fixes common data corruption issues introduced by spreadsheet applications (such as Microsoft Excel and Google Sheets) when user inputs are auto-formatted into clock times (`HH:MM:SS`), preparing entries for seamless import into meet management software (such as Hy-Tek Meet Manager or Splash).

---

## Background & Purpose

When swimmers or club administrators submit entry times into spreadsheets or online forms, spreadsheet software often misinterprets swim times as wall-clock times:
- **Sprint times (25m and 50m):** 36 seconds entered as `00:00:36`, `00:36:00`, or `36:00` gets converted into hours/minutes or hundredths. Times with hundredths like `29.37` entered with a colon (`29:37`) become `00:29:37`.
- **Middle-distance times (100m to 400m):** Times like 1 minute 45 seconds entered as `1:45` get parsed into clock hours as `01:45:00`.
- **Long-distance times (800m and 1500m):** Times over 9:59 entered as whole minutes or clock times (e.g. `13` or `00:13:00` for an 800m Free) risk being misparsed as 13 seconds or decimal seconds unless explicit `MM:SS.SS` format is used.

`clean_times.py` automatically detects event distances and resolves these formatting discrepancies into standard swim software seed formats.

---

## Standard Output Formats

| Event Category | Distance | Target Format | Examples |
| :--- | :--- | :--- | :--- |
| **Sprint** | 25m, 50m (< 1 min) | `SS.SS` | `36.00`, `29.37`, `13.54` |
| **Sprint (Slow)** | 50m (>= 1 min) | `M:SS.SS` | `1:03.00`, `1:10.00`, `1:31.00` |
| **Middle-Distance** | 100m to 400m (1:00 to 9:59) | `M:SS.SS` | `1:08.00`, `1:30.95`, `6:00.00` |
| **Long-Distance** | 800m, 1500m (>= 10:00) | `MM:SS.SS` | `13:00.00`, `19:07.00`, `26:00.00` |
| **Sub-minute 100m** | 100m Free (< 1 min) | `SS.SS` | `55.00` |
| **No Time / Zero** | Any event | `0:00.00` or `NT` | `0:00.00`, `NT` |

---

## Key Features

- **Universal Column Detection:**
  - **Paired Columns:** Automatically identifies numbered pairs such as `Event 1` / `Time 1 (m:s.S)` through `Event 14` / `Time 14`.
  - **Event-Named Headers:** Automatically detects columns named directly after swim events (e.g., `50 Free`, `100 Back`, `400 Free`, `1,500 Free`, `200 any stroke`).
  - **Generic Time Columns:** Detects `Time` or `Seed Time` headers preceded by `Event` columns.
- **Data Integrity:** Only modifies entry time values; swimmer names, dates of birth, clubs, genders, event names, and blank cells are preserved intact.
- **Excel UTF-8 BOM Support:** Reads and writes using `utf-8-sig` by default to prevent character corruption when opening files in Excel.
- **Zero External Dependencies:** Built using Python's standard library (`argparse`, `csv`, `re`, `shutil`, `sys`).

---

## Requirements

- Python 3.6 or newer.
- No external packages required.

---

## CLI Options

```
python clean_times.py [-h] [-i INPUT_FILE] [-o OUTPUT_FILE] [--in-place] [-d]
                      [-t] [-v] [--backup] [--encoding ENCODING]
```

### Complete Options List

| Option | Flag(s) | Description | Default |
| :--- | :--- | :--- | :--- |
| **Help** | `-h`, `--help` | Show the help message and exit. | — |
| **Input File** | `-i`, `--input`, `--input-file` | Path to the input CSV file. | `Masters Spring Fling 2026 - INDIVIDUAL_EVENTS_TEMPLATE.csv` |
| **Output File** | `-o`, `--output`, `--output-file` | Path to save the cleaned CSV file. | `<input>-cleaned.csv` |
| **In-Place** | `--in-place` | Overwrite the input file directly instead of creating a new file. | `False` |
| **Dry Run** | `-d`, `--dry-run` | Validate and preview normalization statistics without modifying any file. | `False` |
| **Test** | `-t`, `--test` | Run the built-in unit test suite covering all event and format scenarios. | `False` |
| **Verbose** | `-v`, `--verbose` | Print detailed row-by-row and event-by-event transformation actions to the terminal. | `False` |
| **Backup** | `--backup` | Create a `.bak` backup copy of the input file before overwriting or writing in-place. | `False` |
| **Encoding** | `--encoding` | File encoding used for reading and writing CSV files. | `utf-8-sig` |

---

## Usage Examples

### 1. Run Unit Tests
Verify the normalization logic against all test scenarios:
```bash
python clean_times.py --test
```

### 2. Preview & Validate Without Modifying (Dry Run)
Check an entry file to inspect detected columns, valid time counts, and any formatting anomalies:
```bash
python clean_times.py --dry-run -i "spring fling entries 2026.csv"
```

To see individual row-by-row conversion details, add `--verbose`:
```bash
python clean_times.py --dry-run -i "spring fling entries 2026.csv" --verbose
```

### 3. Clean to Default Output File
Cleans the input file and creates an output file named `<input>-cleaned.csv` (e.g., `spring fling entries 2026-cleaned.csv`):
```bash
python clean_times.py -i "spring fling entries 2026.csv"
```

### 4. Clean to a Custom Output File
Specify an explicit output path:
```bash
python clean_times.py -i "spring fling entries 2026.csv" -o "final_entries.csv"
```

### 5. Overwrite File In-Place with Automatic Backup
Update the input CSV file directly while creating a `.bak` backup copy for safety:
```bash
python clean_times.py -i "spring fling entries 2026.csv" --in-place --backup
```

---

## Normalization Logic Details

1. **`00:00:SS`:** Seconds entered into the third clock component are extracted as `SS.00` (e.g., `00:00:32` -> `32.00`).
2. **`00:MM:00` in Sprints:** Trailing zeros representing minutes/seconds confusion are converted to `SS.00` (e.g., `00:36:00` -> `36.00`).
3. **`00:SS:ss` in Sprints:** Hundredths entered with colons are converted to decimal seconds `SS.ss` (e.g., `00:29:37` -> `29.37`).
4. **`HH:MM:00` in Distance:** Hour values representing minutes are shifted to `M:SS.00` or `MM:SS.00` (e.g., `01:45:00` -> `1:45.00`, `04:40:00` -> `4:40.00`).
5. **`00:MM:SS` in Distance:** Leading zero hours are stripped to produce `M:SS.00` for under 10 minutes (e.g., `00:01:08` -> `1:08.00`, `00:06:00` -> `6:00.00`) and full `MM:SS.00` for 10 minutes and over (e.g., `00:13:00` -> `13:00.00`, `00:26:00` -> `26:00.00`).
6. **Whole numbers in Long Distance:** Integer minute entries (e.g., `13` for 800m Free) are converted to full `MM:SS.SS` (`13:00.00`).
7. **Zero / NT:** Zero times (`00:00:00`, `0:00`, `0`) become `0:00.00`; `NT`, `N/T`, or `No Time` become `NT`.
