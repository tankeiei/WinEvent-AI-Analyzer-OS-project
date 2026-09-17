"""Data Models for WinEvent Analyzer."""

from datetime import datetime
import hashlib
from typing import Optional, Literal
from pydantic import BaseModel, Field


class CrashEvent(BaseModel):
    """
    Represents an application crash or hang event captured from Windows Event Log.
    Supports:
      - Event ID 1000: Application Error (Crash)
      - Event ID 1001: Windows Error Reporting (WER Telemetry)
      - Event ID 1002: Application Hang (Window/Process Freeze)
    """

    event_id: int = Field(default=1000, description="Windows Event ID (1000=Crash, 1001=WER, 1002=Hang)")
    event_type: Literal["CRASH", "HANG"] = Field(default="CRASH", description="Classification: CRASH or HANG")
    record_id: Optional[int] = Field(default=None, description="Event Log Record ID")
    time_created: str = Field(..., description="Timestamp when the event was recorded (ISO 8601 or formatted)")
    
    app_name: str = Field(..., description="Name of the faulting or hanging application (e.g. Discord.exe)")
    app_version: Optional[str] = Field(default=None, description="Application version")
    app_path: Optional[str] = Field(default=None, description="Absolute file path of the application")
    
    module_name: Optional[str] = Field(default=None, description="Faulting module (DLL/exe) for crash events")
    module_version: Optional[str] = Field(default=None, description="Faulting module version")
    module_path: Optional[str] = Field(default=None, description="Absolute file path of the module")
    
    exception_code: Optional[str] = Field(default="N/A", description="Hexadecimal exception code (e.g. 0xc0000005)")
    exception_symbol: Optional[str] = Field(default=None, description="NTSTATUS / Win32 constant (e.g. STATUS_ACCESS_VIOLATION)")
    exception_meaning: Optional[str] = Field(default=None, description="Human-friendly explanation in Thai")
    
    hang_type: Optional[str] = Field(default=None, description="Hang classification e.g. 'Top level window is idle'")
    fault_offset: Optional[str] = Field(default=None, description="Memory offset where the fault occurred")
    process_id: Optional[str] = Field(default=None, description="Process ID (PID) of the application")
    report_id: Optional[str] = Field(default=None, description="Windows Error Reporting GUID")
    
    @property
    def signature_hash(self) -> str:
        """Computes an MD5 signature hash for caching AI diagnosis results."""
        norm_type = (self.event_type or "CRASH").lower().strip()
        norm_app = (self.app_name or "").lower().strip()
        norm_mod = (self.module_name or "").lower().strip()
        norm_exc = (self.exception_code or "").lower().strip()
        key = f"{norm_type}:{norm_app}:{norm_mod}:{norm_exc}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()


class CrashFilterQuery(BaseModel):
    """Query parameters for filtering crash and hang events."""

    hours: int = Field(default=24, ge=1, le=720, description="Fetch events within the last N hours")
    event_type: Optional[Literal["ALL", "CRASH", "HANG"]] = Field(default="ALL", description="Filter by event type")
    app_name: Optional[str] = Field(default=None, description="Filter by application name")
    limit: int = Field(default=50, ge=1, le=500, description="Max number of events to return")
