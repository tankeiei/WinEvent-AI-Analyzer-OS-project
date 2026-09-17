"""FastAPI Backend Server for WinEvent Analyzer."""

import os
import sys
import platform
import asyncio
import subprocess
from typing import Optional, Literal
from pathlib import Path

from fastapi import FastAPI, Query, HTTPException, BackgroundTasks
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
    version="1.0.0"
)

# Enable CORS for local development
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


@app.get("/api/events")
async def fetch_events(
    hours: int = Query(default=48, ge=1, le=720),
    limit: int = Query(default=50, ge=1, le=300),
    type: Literal["ALL", "CRASH", "HANG"] = Query(default="ALL"),
    app: Optional[str] = Query(default=None),
):
    """Retrieves normalized Crash and Hang events from Windows Event Viewer."""
    try:
        # Run blocking event extraction in async executor so it doesn't freeze the event loop
        loop = asyncio.get_event_loop()
        events = await loop.run_in_executor(
            None, get_crash_events, hours, limit, type, app
        )
        return {
            "total": len(events),
            "filters": {
                "hours": hours,
                "type": type,
                "app": app,
                "limit": limit
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
    
    # Run the simulator in an independent subprocess
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
