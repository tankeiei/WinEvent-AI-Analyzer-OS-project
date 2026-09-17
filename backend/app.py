"""FastAPI Backend Server for WinEvent Analyzer."""

import os
import sys
import platform
import asyncio
import subprocess
from collections import Counter
from typing import Optional, Literal
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.extractor.event_reader import get_crash_events, HAS_PYWIN32
from backend.models import CrashEvent

app = FastAPI(
    title="WinEvent Analyzer API",
    description="OS Crash & Hang Telemetry Monitoring and Diagnosis Backend",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = PROJECT_ROOT / "frontend"


class SimulationRequest(BaseModel):
    simulation_type: str = "fail_fast"


@app.get("/api/system-info")
async def get_system_info():
    """Returns local host environment and telemetry engine status."""
    return {
        "os_name": f"{platform.system()} {platform.release()} (Build {platform.version()})",
        "machine_name": platform.node(),
        "python_version": platform.python_version(),
        "engine_mode": "pywin32 (Native C-API)" if HAS_PYWIN32 else "PowerShell Fallback",
        "has_native_api": HAS_PYWIN32,
        "log_channel": "Application",
        "monitored_events": [
            {"id": 1000, "name": "Application Error", "type": "CRASH"},
            {"id": 1001, "name": "Windows Error Reporting", "type": "CRASH"},
            {"id": 1002, "name": "Application Hang", "type": "HANG"}
        ]
    }


@app.get("/api/stats")
async def get_system_stats(
    hours: int = Query(default=168, ge=1, le=720)
):
    """Computes summary KPI metrics across the requested time window."""
    loop = asyncio.get_event_loop()
    events = await loop.run_in_executor(None, get_crash_events, hours, 500, "ALL", None)

    total = len(events)
    crashes = sum(1 for e in events if e.event_type == "CRASH")
    hangs = sum(1 for e in events if e.event_type == "HANG")

    app_counter = Counter(e.app_name for e in events if e.app_name)
    top_apps = [{"name": name, "count": count} for name, count in app_counter.most_common(8)]

    cat_counter = Counter(e.category for e in events if e.category)
    top_categories = [{"category": cat, "count": count} for cat, count in cat_counter.most_common(6)]

    code_counter = Counter(e.exception_code for e in events if e.exception_code and e.exception_code != "N/A")
    top_code = code_counter.most_common(1)[0][0] if code_counter else "None"

    return {
        "hours": hours,
        "total_events": total,
        "total_crashes": crashes,
        "total_hangs": hangs,
        "top_failing_app": top_apps[0]["name"] if top_apps else "None",
        "top_failing_app_count": top_apps[0]["count"] if top_apps else 0,
        "top_exception_code": top_code,
        "top_apps": top_apps,
        "top_categories": top_categories,
    }


@app.get("/api/events")
async def fetch_events(
    hours: int = Query(default=48, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    type: Literal["ALL", "CRASH", "HANG"] = Query(default="ALL"),
    category: Optional[str] = Query(default=None),
    app: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default="time_desc"),
):
    """Retrieves normalized Crash and Hang events with rich multi-facet filtering."""
    try:
        # Normalize parameter values if called directly as Python function without FastAPI DI
        h_val = hours if isinstance(hours, int) else 48
        l_val = limit if isinstance(limit, int) else 100
        t_val = type if isinstance(type, str) else "ALL"
        c_val = category if isinstance(category, str) and category != "ALL" else None
        a_val = app if isinstance(app, str) and app.strip() else None
        s_val = sort_by if isinstance(sort_by, str) else "time_desc"

        loop = asyncio.get_event_loop()
        events = await loop.run_in_executor(
            None, get_crash_events, h_val, l_val, t_val, a_val
        )

        # Apply Category Filter if specified
        if c_val:
            cat_upper = c_val.upper().strip()
            events = [e for e in events if e.category.upper() == cat_upper]

        # Apply Sorting
        if s_val == "time_asc":
            events.sort(key=lambda e: e.time_created or "")
        elif s_val == "app_asc":
            events.sort(key=lambda e: (e.app_name or "").lower())
        else:  # time_desc
            events.sort(key=lambda e: e.time_created or "", reverse=True)

        return {
            "total": len(events),
            "filters": {
                "hours": h_val,
                "type": t_val,
                "category": c_val,
                "app": a_val,
                "sort_by": s_val,
                "limit": l_val
            },
            "events": [e.model_dump() for e in events]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulate")
async def trigger_simulation(req: SimulationRequest):
    """Safely simulates an isolated crash or hang event in a child process."""
    valid_types = ["fatal_exit", "fail_fast", "breakpoint", "gui_freeze"]
    if req.simulation_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid simulation type. Choose from: {valid_types}"
        )

    sim_script = PROJECT_ROOT / "scripts" / "crash_simulator.py"
    
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(sim_script),
            "--type",
            req.simulation_type,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        return {
            "status": "success",
            "simulation_type": req.simulation_type,
            "exit_code": proc.returncode,
            "message": "Simulation completed. Windows Event Log has been updated.",
            "output": stdout.decode("utf-8", errors="replace")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")


# Serve Frontend static assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def serve_index():
    """Serves the main single-page application dashboard."""
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse(
        status_code=404,
        content={"message": "Frontend index.html not found"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
