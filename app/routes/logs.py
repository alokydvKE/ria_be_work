import os
import pandas as pd
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.database import engine
from app.models.projects import Projects, ProjectCreate
from app.services.auth import get_current_user


def get_logs_as_df(folder_path: str, start: datetime, end: datetime) -> pd.DataFrame:
    # 1. Generate the date string
    date_strings = []
    curr = start
    while curr <= end:
        date_strings.append(curr.strftime("%d-%m-%Y"))
        curr += timedelta(days=1)
    
    print(f"---> Searching for dates: {date_strings}")

    all_dfs = []
    try:
        all_files = os.listdir(folder_path)
        print(f"---> Files found in folder: {len(all_files)}")

        search_patterns = []
        for d in date_strings:
            search_patterns.append(d) 
            # Remove leading zero from month (e.g., -04- becomes -4-)
            search_patterns.append(d.replace("-0", "-"))
            # Remove leading zero from day (e.g., 05- becomes 5-)
            if d.startswith("0"):
                search_patterns.append(d[1:])
        
        # 2. Let's be more aggressive with the matching
        files_to_read = []
        for f in all_files:
            if any(pattern in f for pattern in search_patterns):
                files_to_read.append(f)
        
        print(f"---> Patterns attempted: {search_patterns}")
        print(f"---> Successfully matched files: {files_to_read}")

        for filename in files_to_read:
            file_path = os.path.join(folder_path, filename)
            try:
                # Use a more robust line-by-line reader in case one line is corrupt
                df = pd.read_json(file_path, lines=True)
                if not df.empty:
                    df['_filename'] = filename
                    all_dfs.append(df)
                    print(f"---> Successfully read {filename} ({len(df)} rows)")
            except Exception as e:
                print(f"---> ERROR reading {filename}: {e}")
                
        if not all_dfs:
            return pd.DataFrame()

        return pd.concat(all_dfs, ignore_index=True)
    except Exception as e:
        print(f"---> Directory error: {e}")
       
    return pd.DataFrame()



router = APIRouter()

@router.get("/{project_id}/logs")
def get_logs(
    project_id: int,
    date_range: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    level: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1),
    user=Depends(get_current_user)
):
    with Session(engine) as session:
        project = session.get(Projects, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

    dr = date_range.lower() if date_range else "latest"
    start = end = None

    if dr == "latest":
        try:
            all_files = os.listdir(project.location)
            found_dates = []
            
            for f in all_files:
                if "_" in f:
                    date_part = f.split('_')[0]
                    try:
                        # 4-digit year
                        parsed_date = datetime.strptime(date_part, "%d-%m-%Y")
                        found_dates.append(parsed_date)
                    except:
                        continue
            
            if found_dates:
                latest_dt = max(found_dates)
                start = latest_dt.replace(hour=0, minute=0, second=0)
                end = latest_dt.replace(hour=23, minute=59, second=59)
                print(f"found latest logs on: {start.strftime('%d-%m-%Y')}")
        except Exception as e:
            print(f"Discovery error: {e}")

    # Fallback to 24h ago if no files found or discovery failed
    if not start:
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=1)
        end = now


    df = get_logs_as_df(project.location, start, end)
    
    if df.empty:
        return {"total": 0, "logs": [], "pages": 0, "active_range": {"from": start.isoformat(), "to": end.isoformat()}}

    # Filter by Level
    if level:
        # Check if 'level' column exists and filter
        if 'level' in df.columns:
            df = df[df['level'].astype(str).str.upper() == level.upper()]

    # Filter by Keyword
    if keyword:
        # Search all columns
        mask = df.astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)
        df = df[mask]

    # Sort by timestamp
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.sort_values(by='timestamp', ascending=False)

    # Paginate
    total = len(df)
    start_idx = (page - 1) * page_size
    # .copy() ensures we don't get 'SettingWithCopy' warnings
    subset = df.iloc[start_idx : start_idx + page_size].copy()
    
    # 1. Handle Datetime columns correctly
    for col in subset.columns:
        if pd.api.types.is_datetime64_any_dtype(subset[col]):
            # Use .astype(str) or map to isoformat to make it JSON friendly
            subset[col] = subset[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)

    # 2. Convert everything to object type so we can swap NaN for None
    # This is what prevents the 'Out of range float values' error
    clean_subset = subset.astype(object).where(pd.notnull(subset), None)
    
    paginated_logs = clean_subset.to_dict(orient="records")

    return {
        "total": total,
        "page": page,
        "pages": -(-total // page_size) if page_size > 0 else 0,
        "logs": paginated_logs,
        "active_range": {"from": start.isoformat(), "to": end.isoformat()}
    }