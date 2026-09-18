"""Local FastAPI server for the WinEvent Analyzer dashboard."""

import asyncio
from collections import Counter
from datetime import datetime, timezone
import platform
from pathlib import Path
import subprocess
import sys
from threading import Lock
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.ai_engine.gemini_analyzer import DiagnosisService
from backend.config import get_settings
from backend.database import DiagnosisCache
from backend.extractor.event_reader import HAS_PYWIN32, read_event_log
from backend.extractor.error_codes import lookup_diagnostic
from backend.models import (
    AnalyzeRequest,
    CrashEvent,
    DashboardResponse,
    DashboardStats,
    DiagnosisResponse,
    EventFilterType,
)


settings = get_settings()
diagnosis_service = DiagnosisService(settings=settings)
cache = DiagnosisCache(settings.cache_db_path)

app = FastAPI(
    title="WinEvent Analyzer API",
    description="Local Windows crash and hang telemetry diagnosis dashboard",
    version=settings.app_version,
)

FRONTEND_DIR = PROJECT_ROOT / "frontend"
FRONTEND_BUILD_DIR = FRONTEND_DIR / "dist"


class SimulationRequest(BaseModel):
    simulation_type: Literal[
        "fatal_exit", "access_violation", "fail_fast", "breakpoint", "gui_freeze"
    ] = "fail_fast"


_simulation_events: list[CrashEvent] = []
_simulation_events_lock = Lock()


def _build_simulation_event(simulation_type: str) -> CrashEvent:
    """Create a transparent local fallback when Windows emits no short-lived demo event."""
    now = datetime.now(timezone.utc)
    record_id = -int(now.timestamp() * 1000)
    if simulation_type == "gui_freeze":
        diagnostic = lookup_diagnostic("APPLICATION_HANG")
        return CrashEvent(
            event_id=1002,
            event_type="HANG",
            record_id=record_id,
            time_created=now.isoformat(),
            app_name="WinEvent GUI Hang Demo",
            app_version="demo",
            module_name="UI Message Loop / Thread",
            exception_code="N/A",
            exception_symbol=diagnostic.symbol,
            category=diagnostic.category,
            category_label=diagnostic.category_label,
            severity=diagnostic.severity,
            exception_meaning=diagnostic.meaning,
            offline_checks=diagnostic.suggested_checks,
            hang_type="Top level window is idle (simulated)",
            report_id="SIMULATION:gui_freeze",
        )

    exception_code = "0xc0000005" if simulation_type == "access_violation" else "0xc0000409"
    diagnostic = lookup_diagnostic(exception_code)
    is_access_violation = simulation_type == "access_violation"
    return CrashEvent(
        event_id=1000,
        event_type="CRASH",
        record_id=record_id,
        time_created=now.isoformat(),
        app_name=(
            "WinEvent Access Violation Demo"
            if is_access_violation
            else "WinEvent C-Runtime Demo"
        ),
        app_version="demo",
        module_name="kernel32.dll" if is_access_violation else "ucrtbase.dll",
        exception_code=exception_code,
        exception_symbol=diagnostic.symbol,
        category=diagnostic.category,
        category_label=(
            "Access Violation (simulated)"
            if is_access_violation
            else "C-Runtime abort (simulated)"
        ),
        severity=diagnostic.severity,
        exception_meaning=(
            diagnostic.meaning
            if is_access_violation
            else "Universal C Runtime abort() จบการทำงานของ process แบบฉุกเฉินเพื่อทดสอบการตรวจจับ Application Error"
        ),
        offline_checks=diagnostic.suggested_checks,
        report_id=f"SIMULATION:{simulation_type}",
    )


def _get_simulation_events(hours: int, event_type: EventFilterType) -> list[CrashEvent]:
    cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
    with _simulation_events_lock:
        recent: list[CrashEvent] = []
        active: list[CrashEvent] = []
        for event in _simulation_events:
            try:
                event_timestamp = datetime.fromisoformat(
                    event.time_created.replace("Z", "+00:00")
                ).timestamp()
            except ValueError:
                continue
            if event_timestamp >= cutoff:
                active.append(event)
            if event_timestamp >= cutoff and (
                event_type == "ALL" or event.event_type == event_type
            ):
                recent.append(event)
        _simulation_events[:] = active
        return recent


def _sort_events(events: list[CrashEvent], sort_by: str) -> list[CrashEvent]:
    if sort_by == "time_asc":
        return sorted(events, key=lambda event: event.time_created or "")
    if sort_by == "app_asc":
        return sorted(events, key=lambda event: (event.app_name or "").lower())
    return sorted(events, key=lambda event: event.time_created or "", reverse=True)


def _make_stats(events: list[CrashEvent], hours: int) -> DashboardStats:
    app_counter = Counter(event.app_name for event in events if event.app_name)
    category_counter = Counter(event.category for event in events if event.category)
    code_counter = Counter(
        event.exception_code
        for event in events
        if event.exception_code and event.exception_code != "N/A"
    )
    return DashboardStats(
        hours=hours,
        total_events=len(events),
        total_crashes=sum(event.event_type == "CRASH" for event in events),
        total_hangs=sum(event.event_type == "HANG" for event in events),
        total_critical=sum(event.severity == "CRITICAL" for event in events),
        total_high=sum(event.severity == "HIGH" for event in events),
        top_failing_app=app_counter.most_common(1)[0][0] if app_counter else "None",
        top_failing_app_count=app_counter.most_common(1)[0][1] if app_counter else 0,
        top_exception_code=code_counter.most_common(1)[0][0]
        if code_counter
        else "None",
        top_apps=[{"name": name, "count": count} for name, count in app_counter.most_common(8)],
        top_categories=[
            {"category": category, "count": count}
            for category, count in category_counter.most_common(8)
        ],
    )


def _read_dashboard_events(
    hours: int,
    limit: int,
    event_type: EventFilterType,
    category: Optional[str],
    app_name: Optional[str],
    sort_by: str,
) -> DashboardResponse:
    # Read once with a larger cap so KPIs describe the whole selected window.
    result = read_event_log(hours, 500, event_type, app_name)
    events = result.events + _get_simulation_events(hours, event_type)
    if event_type != "ALL":
        events = [event for event in events if event.event_type == event_type]
    category_value = category if category and category != "ALL" else None
    if category_value:
        events = [
            event
            for event in events
            if event.category.upper() == category_value.upper().strip()
        ]
    events = _sort_events(events, sort_by)
    return DashboardResponse(
        events=events[:limit],
        stats=_make_stats(events, hours),
        extractor=result.metadata,
        filters={
            "hours": hours,
            "type": event_type,
            "category": category_value,
            "app": app_name,
            "sort_by": sort_by,
            "limit": limit,
        },
        scanned_at=datetime.now(timezone.utc),
    )


@app.get("/api/system-info")
async def get_system_info():
    """Return local capabilities without claiming a successful scan."""
    return {
        "app_version": settings.app_version,
        "os_name": f"{platform.system()} {platform.release()} (Build {platform.version()})",
        "machine_name": platform.node(),
        "python_version": platform.python_version(),
        "native_api_available": HAS_PYWIN32,
        "ai_configured": settings.ai_configured,
        "cache_ready": cache.is_ready(),
        "log_channel": "Application",
        "monitored_events": [
            {"id": 1000, "name": "Application Error", "type": "CRASH"},
            {"id": 1001, "name": "Windows Error Reporting", "type": "CRASH"},
            {"id": 1002, "name": "Application Hang", "type": "HANG"},
        ],
    }


@app.get("/api/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    hours: int = Query(default=48, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    type: EventFilterType = Query(default="ALL"),
    category: Optional[str] = Query(default=None),
    app: Optional[str] = Query(default=None),
    sort_by: str = Query(default="time_desc"),
):
    return await asyncio.to_thread(
        _read_dashboard_events, hours, limit, type, category, app, sort_by
    )


@app.get("/api/stats", response_model=DashboardStats)
async def get_system_stats(hours: int = Query(default=168, ge=1, le=720)):
    snapshot = await asyncio.to_thread(
        _read_dashboard_events, hours, 500, "ALL", None, None, "time_desc"
    )
    return snapshot.stats


@app.get("/api/events")
async def fetch_events(
    hours: int = Query(default=48, ge=1, le=720),
    limit: int = Query(default=100, ge=1, le=500),
    type: EventFilterType = Query(default="ALL"),
    category: Optional[str] = Query(default=None),
    app: Optional[str] = Query(default=None),
    sort_by: str = Query(default="time_desc"),
):
    snapshot = await asyncio.to_thread(
        _read_dashboard_events, hours, limit, type, category, app, sort_by
    )
    return {
        "total": snapshot.stats.total_events,
        "filters": snapshot.filters,
        "extractor": snapshot.extractor,
        "events": [event.model_dump(mode="json") for event in snapshot.events],
    }


@app.post("/api/analyze", response_model=DiagnosisResponse)
async def analyze_event(request: AnalyzeRequest):
    return await asyncio.to_thread(
        diagnosis_service.diagnose, request.event, request.force_refresh
    )


@app.post("/api/simulate")
async def trigger_simulation(request: SimulationRequest):
    sim_script = PROJECT_ROOT / "scripts" / "crash_simulator.py"
    try:
        process = await asyncio.create_subprocess_exec(
            sys.executable,
            str(sim_script),
            "--type",
            request.simulation_type,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        demo_event = None
        message = "Simulation completed. Windows Event Log may need a moment to update."
        if process.returncode == 0 and request.simulation_type == "gui_freeze":
            demo_event = _build_simulation_event(request.simulation_type)
            with _simulation_events_lock:
                _simulation_events.append(demo_event)
            message = (
                "Simulation completed. Windows did not emit a short-lived Event ID 1002, "
                "so a clearly labeled local demo incident was added."
            )
        return {
            "status": "success" if process.returncode == 0 else "completed_with_error",
            "simulation_type": request.simulation_type,
            "exit_code": process.returncode,
            "message": message,
            "demo_event": demo_event.model_dump(mode="json") if demo_event else None,
            "output": stdout.decode("utf-8", errors="replace"),
            "error": stderr.decode("utf-8", errors="replace"),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Simulation failed: {exc}") from exc


if FRONTEND_BUILD_DIR.exists():
    # Only expose the Vite production output. Source files and node_modules stay local.
    app.mount("/static", StaticFiles(directory=str(FRONTEND_BUILD_DIR)), name="static")


@app.get("/")
async def serve_index():
    index_file = FRONTEND_BUILD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse(
        status_code=503,
        content="""<!doctype html>
<html lang="th"><head><meta charset="utf-8"><title>WinEvent Analyzer - Build required</title>
<style>body{font-family:system-ui,sans-serif;background:#07101d;color:#e2e8f0;display:grid;place-items:center;min-height:100vh;margin:0}.card{max-width:620px;padding:32px;border:1px solid #334155;border-radius:18px;background:#0c1728}code{display:block;margin-top:18px;padding:14px;border-radius:10px;background:#020617;color:#67e8f9;white-space:pre-wrap}</style></head>
<body><main class="card"><h1>Frontend build ยังไม่พร้อม</h1><p>ติดตั้ง dependencies และ build React frontend ก่อนเปิดระบบ:</p><code>cd frontend
npm install
npm run build
cd ..
run.bat</code></main></body></html>""",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000)
