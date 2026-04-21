import os
import re
import json
from datetime import datetime, date
from typing import Optional
from app.utils.file_helpers import get_jsonl_path, get_meta_path, is_todays_file, is_valid_filename, sort_files_chronologically


TIMESTAMP_KEYS = {"timestamp", "time", "ts", "datetime", "date", "t"}
LEVEL_KEYS = {"level", "severity", "log_level", "loglevel", "lvl", "type"}
MESSAGE_KEYS = {"message", "msg", "text", "body", "description", "event", "log"}

TIMESTAMP_PATTERNS = [
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S,%f",
    "%Y-%m-%d %H:%M:%S.%f",
    "%d/%b/%Y:%H:%M:%S",
    "%b %d %H:%M:%S",
]

LEVEL_NORMALISE = {
    "warning":  "WARN",
    "warn":     "WARN",
    "error":    "ERROR",
    "err":      "ERROR",
    "info":     "INFO",
    "debug":    "DEBUG",
    "critical": "ERROR",
    "fatal":    "ERROR",
    "trace":    "DEBUG",
}


def load_meta(project_id: int) -> dict:
    path = get_meta_path(project_id)
    if not os.path.exists(path):
        return {
            "project_id":       project_id,
            "parsed_files":     {},
            "column_map":       {},
            "skipped_files":    [],
            "total_entries":    0,
            "last_sync":        None,
            "detected_columns": [],
            "prev_columns":     [],
            "format_changed":   False,
            "format_warnings":  [],
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_meta(project_id: int, meta: dict):
    meta["parsed_files"] = dict(sorted(meta["parsed_files"].items()))
    with open(get_meta_path(project_id), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, default=str)


def parse_timestamp(value: str) -> Optional[str]:
    if not value:
        return None
    value = value.strip().replace("Z", "")
    for fmt in TIMESTAMP_PATTERNS:
        try:
            return datetime.strptime(value, fmt).isoformat()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(value).isoformat()
    except Exception:
        return None

def normalise_level(value: str) -> str:
    return LEVEL_NORMALISE.get(value.lower().strip(), value.upper().strip())


def detect_format(lines: list[str]) -> dict:
    sample = [l.strip() for l in lines if l.strip()][:20]
    if not sample:
        return {"type": "plaintext"}

    json_hits = 0
    for line in sample:
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                json_hits += 1
        except Exception:
            pass
    if json_hits >= len(sample) * 0.7:
        try:
            obj = json.loads(sample[0])
            keys = list(obj.keys())
            ts_key  = next((k for k in keys if k.lower() in TIMESTAMP_KEYS), None)
            lvl_key = next((k for k in keys if k.lower() in LEVEL_KEYS), None)
            msg_key = next((k for k in keys if k.lower() in MESSAGE_KEYS), None)
            return {
                "type":      "json",
                "ts_col":    ts_key,
                "level_col": lvl_key,
                "msg_col":   msg_key,
                "all_keys":  keys,
            }
        except Exception:
            return {"type": "json", "ts_col": None, "level_col": None, "msg_col": None, "all_keys": []}

    for delimiter in ["|", "\t", ","]:
        counts     = [len(line.split(delimiter)) for line in sample]
        avg        = sum(counts) / len(counts)
        consistent = sum(1 for c in counts if abs(c - avg) <= 1) >= len(sample) * 0.7
        if consistent and avg >= 3:
            first_cols = [c.strip() for c in sample[0].split(delimiter)]
            has_header = all(
                not parse_timestamp(c) and not c.replace(".", "").isdigit()
                for c in first_cols
            )
            if has_header:
                headers  = [c.lower() for c in first_cols]
                ts_col   = next((i for i, h in enumerate(headers) if h in TIMESTAMP_KEYS), None)
                lvl_col  = next((i for i, h in enumerate(headers) if h in LEVEL_KEYS), None)
                msg_col  = next((i for i, h in enumerate(headers) if h in MESSAGE_KEYS), None)
                skip_row = 0
            else:
                headers  = None
                skip_row = None
                ts_col   = next((i for i, v in enumerate(first_cols) if parse_timestamp(v)), None)
                lvl_col  = next(
                    (i for i, v in enumerate(first_cols) if v.lower().strip() in LEVEL_NORMALISE),
                    None
                )
                used    = {ts_col, lvl_col}
                msg_col = max(
                    (i for i in range(len(first_cols)) if i not in used),
                    key=lambda i: len(first_cols[i]),
                    default=None
                )
            return {
                "type":      "delimited",
                "delimiter": delimiter,
                "headers":   headers,
                "skip_row":  skip_row,
                "ts_col":    ts_col,
                "level_col": lvl_col,
                "msg_col":   msg_col,
                "num_cols":  int(avg),
            }

    return {"type": "plaintext"}


PLAINTEXT_PATTERNS = [
    re.compile(
        r"(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?Z?)"
        r"\s*[-|]\s*(?P<level>INFO|WARN|WARNING|ERROR|DEBUG|CRITICAL)"
        r"\s*[-|]\s*(?P<message>.+)"
    ),
    re.compile(
        r"\[(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})\]"
        r"\s*(?P<level>INFO|WARN|WARNING|ERROR|DEBUG|CRITICAL)[:\s]+(?P<message>.+)"
    ),
    re.compile(
        r"(?P<level>INFO|WARN|WARNING|ERROR|DEBUG|CRITICAL)"
        r"\s+(?P<timestamp>\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2})"
        r"\s+(?P<message>.+)"
    ),
]


def try_plaintext_parse(line: str) -> Optional[dict]:
    for pattern in PLAINTEXT_PATTERNS:
        m = pattern.match(line)
        if m:
            g = m.groupdict()
            return {
                "timestamp": parse_timestamp(g["timestamp"]) or g["timestamp"],
                "level":     normalise_level(g["level"]),
                "message":   g["message"].strip(),
            }
    return None


def parse_json_line(line: str, fmt: dict, source_file: str) -> Optional[dict]:
    try:
        obj = json.loads(line.strip())
        if not isinstance(obj, dict):
            return None
    except Exception:
        return None

    ts_key  = fmt.get("ts_col")
    lvl_key = fmt.get("level_col")
    msg_key = fmt.get("msg_col")

    entry = {}
    entry["timestamp"] = parse_timestamp(str(obj[ts_key]))  if ts_key  and ts_key  in obj else None
    entry["level"]     = normalise_level(str(obj[lvl_key])) if lvl_key and lvl_key in obj else "RAW"
    entry["message"]   = str(obj[msg_key])                  if msg_key and msg_key in obj else ""

    for k, v in obj.items():
        if k not in (ts_key, lvl_key, msg_key):
            entry[k] = v

    entry["source_file"] = source_file
    return entry


def parse_delimited_line(
    line: str,
    fmt: dict,
    source_file: str,
    line_num: int,
) -> Optional[dict]:
    stripped = line.strip()
    if not stripped:
        return None

    if fmt.get("skip_row") is not None and line_num == 0:
        return None

    parts    = [p.strip() for p in stripped.split(fmt["delimiter"])]
    num_cols = fmt.get("num_cols", len(parts))
    while len(parts) < num_cols:
        parts.append("")

    headers = fmt.get("headers")
    ts_col  = fmt.get("ts_col")
    lvl_col = fmt.get("level_col")
    msg_col = fmt.get("msg_col")

    def get(col):
        if col is None:
            return None
        try:
            return parts[col]
        except IndexError:
            return None

    ts_raw  = get(ts_col)
    lvl_raw = get(lvl_col)
    msg_raw = get(msg_col)

    entry = {
        "timestamp": parse_timestamp(ts_raw) if ts_raw  else None,
        "level":     normalise_level(lvl_raw) if lvl_raw else "RAW",
        "message":   msg_raw.strip()          if msg_raw else stripped,
    }

    used = {ts_col, lvl_col, msg_col}
    for i, value in enumerate(parts):
        if i in used or not value:
            continue
        key = headers[i] if headers and i < len(headers) else f"col_{i}"
        entry[key] = value

    entry["source_file"] = source_file
    return entry


def parse_file_lines(lines: list[str], source_file: str, fmt: dict) -> list[dict]:
    entries = []

    if fmt["type"] == "json":
        for line in lines:
            entry = parse_json_line(line, fmt, source_file)
            if entry:
                entries.append(entry)
        return entries

    if fmt["type"] == "delimited":
        for i, line in enumerate(lines):
            entry = parse_delimited_line(line, fmt, source_file, i)
            if entry:
                entries.append(entry)
        return entries

    current = None
    for line in lines:
        stripped = line.strip()

        if not stripped:
            if current:
                entries.append(current)
                current = None
            continue

        parsed = try_plaintext_parse(stripped)

        if parsed:
            if current:
                entries.append(current)
            current = {**parsed, "source_file": source_file}
        else:
            if current is not None:
                sf = current.pop("source_file")
                if "traceback" not in current:
                    current["traceback"] = stripped
                else:
                    current["traceback"] += "\n" + stripped
                current["source_file"] = sf
            else:
                entries.append({
                    "timestamp":   None,
                    "level":       "RAW",
                    "message":     stripped,
                    "source_file": source_file,
                })

    if current:
        entries.append(current)

    return entries


def _extract_columns(entry: dict) -> list[str]:
    """Return meaningful column names from a parsed entry, excluding internals."""
    return [k for k in entry.keys() if k not in ("_line", "source_file")]


def _diff_columns(baseline: list[str], current: list[str]) -> dict:
    prev = set(baseline)
    curr = set(current)
    added   = sorted(curr - prev)
    removed = sorted(prev - curr)
    return {
        "changed": bool(added or removed),
        "added":   added,
        "removed": removed,
    }


def _sample_columns_from_file(file_path: str, filename: str) -> list[str]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        fmt     = detect_format(lines)
        entries = parse_file_lines(lines[:10], filename, fmt)
        if entries:
            return _extract_columns(entries[0])
    except Exception:
        pass
    return []


def _rebuild_jsonl(project_id: int, raw_folder: str, valid_files: list[str]) -> tuple[dict, int]:
    """
    Wipe and fully rebuild the JSONL from valid_files.
    Returns (new parsed_files dict, total_entry_count).
    """
    jsonl_path   = get_jsonl_path(project_id)
    parsed_files = {}
    total        = 0

    with open(jsonl_path, "w", encoding="utf-8") as out:
        for filename in valid_files:
            file_path = os.path.join(raw_folder, filename)
            today     = is_todays_file(filename)
            first_ts  = None
            last_ts   = None

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()

                fmt     = detect_format(all_lines)
                entries = parse_file_lines(all_lines, filename, fmt)
                count   = 0

                for entry in entries:
                    ts = entry.get("timestamp")
                    if ts:
                        if not first_ts:
                            first_ts = ts
                        last_ts = ts
                    out.write(json.dumps(entry) + "\n")
                    count += 1

                mtime  = os.path.getmtime(file_path)
                record = {
                    "lines_parsed": len(all_lines),
                    "first_ts":     first_ts,
                    "last_ts":      last_ts,
                    "mtime":        mtime,
                    "detected_fmt": fmt["type"],
                }
                if today:
                    record["last_sync"] = datetime.utcnow().isoformat()
                    record["done"]      = False
                else:
                    record["parsed_at"] = datetime.utcnow().isoformat()
                    record["done"]      = True

                parsed_files[filename] = record
                total += count
                print(f"[rebuild] {filename} → {count} entries")

            except Exception as e:
                print(f"[rebuild] Error reading '{filename}': {e}")

    return parsed_files, total


def _scan_format_warnings(
    raw_folder: str,
    valid_files: list[str],
    baseline_cols: list[str],
) -> list[dict]:

    warnings = []
    for filename in valid_files:
        file_path = os.path.join(raw_folder, filename)
        cols      = _sample_columns_from_file(file_path, filename)
        if not cols:
            continue
        diff = _diff_columns(baseline_cols, cols)
        if diff["changed"]:
            warnings.append({
                "file":    filename,
                "added":   diff["added"],
                "removed": diff["removed"],
            })
    return warnings


def sync_project_logs(project_id: int, raw_folder: str) -> dict:
    if not os.path.exists(raw_folder):
        raise FileNotFoundError(f"Raw log folder not found: {raw_folder}")

    meta           = load_meta(project_id)
    already_parsed = meta["parsed_files"]
    skipped        = []


    valid_files = []
    for filename in os.listdir(raw_folder):
        if not os.path.isfile(os.path.join(raw_folder, filename)):
            continue
        valid, reason = is_valid_filename(filename)
        if not valid:
            skipped.append({"file": filename, "reason": reason})
            continue
        if os.path.getsize(os.path.join(raw_folder, filename)) == 0:
            skipped.append({"file": filename, "reason": "empty file"})
            continue
        valid_files.append(filename)

    valid_files = sort_files_chronologically(valid_files)
    valid_set   = set(valid_files)

    #full resync trigger 
    previously_known = set(already_parsed.keys())
    deleted_files    = previously_known - valid_set

    if deleted_files:
        print(f"[sync] Deleted files detected: {deleted_files}. Triggering full rebuild.")
        new_parsed, total = _rebuild_jsonl(project_id, raw_folder, valid_files)

        # new format based on latest file
        newest_cols: list[str] = []
        for filename in reversed(valid_files):
            cols = _sample_columns_from_file(
                os.path.join(raw_folder, filename), filename
            )
            if cols:
                newest_cols = cols
                break

        confirmed_baseline = list(meta.get("detected_columns") or [])
        format_info        = _diff_columns(confirmed_baseline, newest_cols)

        format_warnings = _scan_format_warnings(
            raw_folder, valid_files, confirmed_baseline
        ) if confirmed_baseline else []

        meta["parsed_files"]     = new_parsed
        meta["total_entries"]    = total
        meta["last_sync"]        = datetime.utcnow().isoformat()
        meta["skipped_files"]    = skipped
        meta["detected_columns"] = newest_cols
        meta["format_changed"]   = format_info["changed"]
        meta["prev_columns"]     = confirmed_baseline
        meta["format_warnings"]  = format_warnings
        save_meta(project_id, meta)

        return {
            "new_files":        len(new_parsed),
            "new_entries":      total,
            "skipped_files":    skipped,
            "total_entries":    total,
            "deleted_files":    sorted(deleted_files),
            "rebuilt":          True,
            "format_changed":   format_info["changed"],
            "format_diff":      format_info,
            "detected_columns": newest_cols,
            "prev_columns":     confirmed_baseline,
            "format_warnings":  format_warnings,
        }

    new_entries     = 0
    files_processed = 0
    jsonl_path      = get_jsonl_path(project_id)

    with open(jsonl_path, "a", encoding="utf-8") as out:
        for filename in valid_files:
            today       = is_todays_file(filename)
            file_record = already_parsed.get(filename)
            done        = file_record and file_record.get("done", False)

            if done:
                continue

            file_path  = os.path.join(raw_folder, filename)
            skip_lines = file_record.get("lines_parsed", 0) if file_record else 0
            first_ts   = file_record.get("first_ts") if file_record else None
            last_ts    = None

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()

                total_lines_now = len(all_lines)
                fmt             = detect_format(all_lines)
                print(
                    f"[sync] {filename} detected format: {fmt['type']}"
                    + (f" delimiter='{fmt.get('delimiter')}'" if fmt["type"] == "delimited" else "")
                )

                new_raw_lines  = all_lines[skip_lines:]
                parsed_entries = parse_file_lines(new_raw_lines, filename, fmt)

                file_entries = 0
                for entry in parsed_entries:
                    ts = entry.get("timestamp")
                    if ts:
                        if not first_ts:
                            first_ts = ts
                        last_ts = ts
                    out.write(json.dumps(entry) + "\n")
                    file_entries += 1

                mtime = os.path.getmtime(file_path)

                if today:
                    already_parsed[filename] = {
                        "lines_parsed": total_lines_now,
                        "last_sync":    datetime.utcnow().isoformat(),
                        "first_ts":     first_ts,
                        "last_ts":      last_ts,
                        "mtime":        mtime,
                        "detected_fmt": fmt["type"],
                        "done":         False,
                    }
                else:
                    already_parsed[filename] = {
                        "lines_parsed": total_lines_now,
                        "parsed_at":    datetime.utcnow().isoformat(),
                        "first_ts":     first_ts,
                        "last_ts":      last_ts,
                        "mtime":        mtime,
                        "detected_fmt": fmt["type"],
                        "done":         True,
                    }

                print(f"[sync] {'today' if today else 'done'}: {filename} → {file_entries} entries")
                new_entries     += file_entries
                files_processed += 1

            except Exception as e:
                print(f"[sync] Error reading '{filename}': {e}")
                skipped.append({"file": filename, "reason": str(e)})
                continue

    confirmed_baseline = list(meta.get("detected_columns") or [])

    newest_cols: list[str] = []
    for filename in reversed(valid_files):
        cols = _sample_columns_from_file(
            os.path.join(raw_folder, filename), filename
        )
        if cols:
            newest_cols = cols
            break

    format_info = _diff_columns(confirmed_baseline, newest_cols) if confirmed_baseline else {
        "changed": False, "added": [], "removed": []
    }

#   pattern inconsistency
    format_warnings = _scan_format_warnings(
        raw_folder, valid_files, confirmed_baseline
    ) if confirmed_baseline else []
#meta
    meta["detected_columns"] = newest_cols or confirmed_baseline
    meta["format_changed"]   = format_info["changed"]
    meta["prev_columns"]     = confirmed_baseline if format_info["changed"] else meta.get("prev_columns", [])
    meta["parsed_files"]     = already_parsed
    meta["total_entries"]    = meta.get("total_entries", 0) + new_entries
    meta["last_sync"]        = datetime.utcnow().isoformat()
    meta["skipped_files"]    = skipped
    meta["format_warnings"]  = format_warnings
    save_meta(project_id, meta)

    return {
        "new_files":        files_processed,
        "new_entries":      new_entries,
        "skipped_files":    skipped,
        "total_entries":    meta["total_entries"],
        "deleted_files":    [],
        "rebuilt":          False,
        "format_changed":   format_info["changed"],
        "format_diff":      format_info,
        "detected_columns": newest_cols or confirmed_baseline,
        "prev_columns":     confirmed_baseline if format_info["changed"] else [],
        "format_warnings":  format_warnings,
    }