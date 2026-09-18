"""Shared data contracts for the WinEvent Analyzer application."""

from datetime import datetime, timezone
import hashlib
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, computed_field


EventType = Literal["CRASH", "HANG"]
EventFilterType = Literal["ALL", "CRASH", "HANG"]
ExtractorEngine = Literal["pywin32", "powershell", "unavailable"]
DiagnosisSource = Literal["gemini", "cache", "offline"]


class CrashEvent(BaseModel):
    """Normalized representation of a Windows Application event."""

    event_id: int = Field(default=1000, description="1000=Crash, 1001=WER, 1002=Hang")
    event_type: EventType = Field(default="CRASH")
    record_id: Optional[int] = None
    time_created: str

    app_name: str
    app_version: Optional[str] = None
    app_path: Optional[str] = None

    module_name: Optional[str] = None
    module_version: Optional[str] = None
    module_path: Optional[str] = None

    exception_code: Optional[str] = "N/A"
    exception_symbol: Optional[str] = None

    category: str = "UNKNOWN"
    category_label: str = "ทั่วไป"
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW", "WARNING"] = "MEDIUM"
    exception_meaning: Optional[str] = None
    offline_checks: List[str] = Field(default_factory=list)

    hang_type: Optional[str] = None
    fault_offset: Optional[str] = None
    process_id: Optional[str] = None
    report_id: Optional[str] = None

    @computed_field
    @property
    def signature_hash(self) -> str:
        """Stable non-secret cache identity for equivalent failures."""
        norm_type = (self.event_type or "CRASH").lower().strip()
        norm_app = (self.app_name or "").lower().strip()
        norm_mod = (self.module_name or "").lower().strip()
        norm_exc = (self.exception_code or "").lower().strip()
        key = f"{norm_type}:{norm_app}:{norm_mod}:{norm_exc}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()


class CauseHypothesis(BaseModel):
    cause: str
    likelihood: Literal["HIGH", "MEDIUM", "LOW"]
    reasoning: str


class ResolutionAction(BaseModel):
    tier: Literal["Tier 1: Quick Fix", "Tier 2: System Health", "Tier 3: Advanced"]
    title: str
    steps: List[str]
    command: Optional[str] = None


class AIDiagnosisResult(BaseModel):
    """Structured response shared by Gemini and Offline Diagnosis."""

    simple_summary: str
    technical_explanation: str
    probable_causes: List[CauseHypothesis]
    actionable_resolutions: List[ResolutionAction]
    search_queries: List[str]


class ExtractionMetadata(BaseModel):
    engine_used: ExtractorEngine
    native_available: bool
    fallback_reason: Optional[str] = None
    duration_ms: float = 0.0


class DashboardStats(BaseModel):
    hours: int
    total_events: int
    total_crashes: int
    total_hangs: int
    total_critical: int = 0
    total_high: int = 0
    top_failing_app: str = "None"
    top_failing_app_count: int = 0
    top_exception_code: str = "None"
    top_apps: List[dict] = Field(default_factory=list)
    top_categories: List[dict] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    events: List[CrashEvent]
    stats: DashboardStats
    extractor: ExtractionMetadata
    filters: dict
    scanned_at: datetime


class AnalyzeRequest(BaseModel):
    event: CrashEvent
    force_refresh: bool = False


class DiagnosisResponse(BaseModel):
    signature_hash: str
    source: DiagnosisSource
    model: Optional[str] = None
    diagnosis: AIDiagnosisResult
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    warning: Optional[str] = None


class CrashFilterQuery(BaseModel):
    hours: int = Field(default=24, ge=1, le=720)
    event_type: Optional[EventFilterType] = "ALL"
    category: Optional[str] = None
    app_name: Optional[str] = None
    sort_by: Optional[str] = "time_desc"
    limit: int = Field(default=50, ge=1, le=500)
