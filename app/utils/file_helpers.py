import os
import re
from datetime import datetime, date
from pathlib import Path

PARSED_LOGS_DIR = "parsed_logs"
DATE_FROM_FILENAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d+)\.")
LOG_EXTENSIONS = {".log", ".txt"}


def get_project_dir(project_id: int) -> str:
    path = os.path.join(PARSED_LOGS_DIR, str(project_id))
    os.makedirs(path, exist_ok=True)
    return path

def get_jsonl_path(project_id: int) -> str:
    return os.path.join(get_project_dir(project_id), "logs.jsonl")

def get_meta_path(project_id: int) -> str:
    return os.path.join(get_project_dir(project_id), "meta.json")


def is_valid_filename(filename: str) -> tuple[bool, str]:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in LOG_EXTENSIONS:
        return False, f"unsupported extension '{ext}'"
    m = DATE_FROM_FILENAME.match(filename)
    if not m:
        return False, "filename must follow YYYY-MM-DD_N.log format"
    try:
        datetime.strptime(m.group(1), "%Y-%m-%d")
    except ValueError:
        return False, f"'{m.group(1)}' is not a valid date"
    return True, ""

def extract_sort_key(filename: str) -> tuple:
    m = DATE_FROM_FILENAME.match(filename)
    if m:
        return (m.group(1), int(m.group(2)))
    return ("9999-99-99", 0)

def sort_files_chronologically(filenames: list[str]) -> list[str]:
    return sorted(filenames, key=extract_sort_key)

def is_todays_file(filename: str) -> bool:
    m = DATE_FROM_FILENAME.match(filename)
    if not m:
        return False
    try:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date() == date.today()
    except Exception:
        return False

