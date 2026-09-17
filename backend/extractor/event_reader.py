"""Event Reader module: extracts Application Error events from Windows Event Log."""

import subprocess
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from backend.models import CrashEvent
from backend.extractor.parser import parse_event_xml

logger = logging.getLogger(__name__)

# Try importing pywin32 for native C-level extraction
try:
    import win32evtlog
    import win32evtlogutil
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False


def _fetch_via_pywin32(hours: int, max_events: int) -> List[CrashEvent]:
    """Extracts events using the native Windows Event Log C-API (pywin32)."""
    if not HAS_PYWIN32:
        return []

    events: List[CrashEvent] = []
    # XPath query: Application channel, Provider 'Application Error', EventID 1000
    # Time filter: milliseconds since event
    ms_ago = int(hours * 3600 * 1000)
    query_xpath = (
        f"*[System[Provider[@Name='Application Error'] and (EventID=1000) "
        f"and TimeCreated[timediff(@SystemTime) <= {ms_ago}]]]"
    )

    try:
        flags = win32evtlog.EvtQueryChannelPath | win32evtlog.EvtQueryReverseDirection
        query_handle = win32evtlog.EvtQuery(None, "Application", query_xpath, flags)
        
        while len(events) < max_events:
            event_handles = win32evtlog.EvtNext(query_handle, min(10, max_events - len(events)))
            if not event_handles:
                break
            for h in event_handles:
                xml_str = win32evtlog.EvtRender(None, h, win32evtlog.EvtRenderEventXml)
                parsed = parse_event_xml(xml_str)
                if parsed:
                    events.append(parsed)
    except Exception as e:
        logger.warning(f"pywin32 extraction failed, falling back to PowerShell: {e}")
        return []

    return events


def _fetch_via_powershell(hours: int, max_events: int) -> List[CrashEvent]:
    """Extracts events using PowerShell Get-WinEvent as a reliable, zero-dependency fallback."""
    events: List[CrashEvent] = []

    # PowerShell command to fetch events and wrap each ToXml() with delimiter tags
    ps_cmd = f"""
    $ErrorActionPreference = 'SilentlyContinue'
    $startTime = (Get-Date).AddHours(-{hours})
    $events = Get-WinEvent -FilterHashtable @{{LogName='Application'; ProviderName='Application Error'; StartTime=$startTime}} -MaxEvents {max_events}
    if ($events) {{
        foreach ($e in $events) {{
            Write-Output "---EVENT_XML_START---"
            Write-Output $e.ToXml()
            Write-Output "---EVENT_XML_END---"
        }}
    }}
    """

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )

        output = result.stdout
        parts = output.split("---EVENT_XML_START---")
        for part in parts:
            if "---EVENT_XML_END---" in part:
                xml_content = part.split("---EVENT_XML_END---")[0].strip()
                if xml_content:
                    parsed = parse_event_xml(xml_content)
                    if parsed:
                        events.append(parsed)

    except Exception as e:
        logger.error(f"PowerShell event extraction error: {e}")

    return events


def get_crash_events(
    hours: int = 24,
    max_events: int = 50,
    app_name: Optional[str] = None,
) -> List[CrashEvent]:
    """
    Retrieves application crash events (Event ID 1000) from the Windows Event Log.
    Automatically prioritizes pywin32 if available, with seamless fallback to PowerShell.
    """
    events: List[CrashEvent] = []

    if HAS_PYWIN32:
        events = _fetch_via_pywin32(hours, max_events)

    # Fallback if pywin32 is not installed or returned empty
    if not events:
        events = _fetch_via_powershell(hours, max_events)

    # If an application filter was requested
    if app_name:
        query_norm = app_name.lower().strip()
        events = [e for e in events if query_norm in e.app_name.lower()]

    return events
