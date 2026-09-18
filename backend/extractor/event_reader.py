"""Windows Event Log extraction with truthful engine/fallback metadata."""

from dataclasses import dataclass
import logging
import subprocess
import time
from typing import List, Literal, Optional, Tuple

from backend.models import CrashEvent, ExtractionMetadata
from backend.extractor.parser import parse_event_xml

logger = logging.getLogger(__name__)

try:
    import win32evtlog

    HAS_PYWIN32 = True
except ImportError:
    win32evtlog = None
    HAS_PYWIN32 = False


EventFilter = Literal["ALL", "CRASH", "HANG"]


@dataclass
class EventReadResult:
    events: List[CrashEvent]
    metadata: ExtractionMetadata


def _build_provider_clause(event_type: str) -> str:
    if event_type == "CRASH":
        return "(Provider[@Name='Application Error'] and (EventID=1000 or EventID=1001))"
    if event_type == "HANG":
        return "(Provider[@Name='Application Hang'] and (EventID=1002))"
    return (
        "(Provider[@Name='Application Error'] and (EventID=1000 or EventID=1001)) "
        "or (Provider[@Name='Application Hang'] and (EventID=1002))"
    )


def _fetch_via_pywin32(
    hours: int, max_events: int, event_type: str = "ALL"
) -> Tuple[List[CrashEvent], Optional[str]]:
    """Use the current pywin32 EvtQuery(Path, Flags, Query) signature."""
    if not HAS_PYWIN32 or win32evtlog is None:
        return [], "pywin32 is not installed"

    ms_ago = int(hours * 3600 * 1000)
    query_xpath = (
        f"*[System[({_build_provider_clause(event_type)}) and "
        f"TimeCreated[timediff(@SystemTime) <= {ms_ago}]]]"
    )
    events: List[CrashEvent] = []

    try:
        flags = win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection
        query_handle = win32evtlog.EvtQuery("Application", flags, query_xpath)

        while len(events) < max_events:
            event_handles = win32evtlog.EvtNext(
                query_handle, min(10, max_events - len(events))
            )
            if not event_handles:
                break
            for event_handle in event_handles:
                xml_str = win32evtlog.EvtRender(
                    event_handle, win32evtlog.EvtRenderEventXml
                )
                parsed = parse_event_xml(xml_str)
                if parsed:
                    events.append(parsed)
        return events, None
    except Exception as exc:
        logger.warning("pywin32 extraction failed: %s", exc)
        return [], str(exc)


def _fetch_via_powershell(
    hours: int, max_events: int, event_type: str = "ALL"
) -> Tuple[List[CrashEvent], Optional[str]]:
    """Use Get-WinEvent as a zero-dependency Windows fallback."""
    if event_type == "CRASH":
        providers = "@('Application Error')"
    elif event_type == "HANG":
        providers = "@('Application Hang')"
    else:
        providers = "@('Application Error', 'Application Hang')"

    ps_cmd = f"""
    $ErrorActionPreference = 'Stop'
    $startTime = (Get-Date).AddHours(-{hours})
    $events = Get-WinEvent -FilterHashtable @{{LogName='Application'; ProviderName={providers}; StartTime=$startTime}} -MaxEvents {max_events}
    if ($events) {{
        foreach ($e in $events) {{
            Write-Output "---EVENT_XML_START---"
            Write-Output $e.ToXml()
            Write-Output "---EVENT_XML_END---"
        }}
    }}
    """
    events: List[CrashEvent] = []
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                ps_cmd,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if result.returncode != 0:
            return [], result.stderr.strip() or "PowerShell Get-WinEvent failed"
        for part in result.stdout.split("---EVENT_XML_START---"):
            if "---EVENT_XML_END---" not in part:
                continue
            xml_content = part.split("---EVENT_XML_END---", 1)[0].strip()
            parsed = parse_event_xml(xml_content)
            if parsed:
                events.append(parsed)
        return events, None
    except Exception as exc:
        logger.error("PowerShell event extraction error: %s", exc)
        return [], str(exc)


def read_event_log(
    hours: int = 24,
    max_events: int = 50,
    event_type: EventFilter = "ALL",
    app_name: Optional[str] = None,
) -> EventReadResult:
    started = time.perf_counter()
    fallback_reason: Optional[str] = None

    if HAS_PYWIN32:
        events, native_error = _fetch_via_pywin32(hours, max_events, event_type)
        if native_error is None:
            engine = "pywin32"
        else:
            fallback_reason = native_error
            events, powershell_error = _fetch_via_powershell(
                hours, max_events, event_type
            )
            engine = "powershell" if powershell_error is None else "unavailable"
            if powershell_error:
                fallback_reason = f"Native: {native_error}; PowerShell: {powershell_error}"
    else:
        events, powershell_error = _fetch_via_powershell(
            hours, max_events, event_type
        )
        engine = "powershell" if powershell_error is None else "unavailable"
        fallback_reason = powershell_error

    if app_name:
        query_norm = app_name.lower().strip()
        events = [e for e in events if query_norm in e.app_name.lower()]

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    return EventReadResult(
        events=events,
        metadata=ExtractionMetadata(
            engine_used=engine,
            native_available=HAS_PYWIN32,
            fallback_reason=fallback_reason,
            duration_ms=duration_ms,
        ),
    )


def get_crash_events(
    hours: int = 24,
    max_events: int = 50,
    event_type: EventFilter = "ALL",
    app_name: Optional[str] = None,
) -> List[CrashEvent]:
    """Compatibility wrapper returning only the normalized event list."""
    return read_event_log(hours, max_events, event_type, app_name).events
