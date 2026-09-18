import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.models import CrashEvent


@pytest.fixture
def crash_event() -> CrashEvent:
    return CrashEvent(
        event_id=1000,
        event_type="CRASH",
        record_id=42,
        time_created="2026-09-18T08:00:00Z",
        app_name="DemoApp.exe",
        app_version="1.2.3",
        app_path="C:\\Users\\Demo\\DemoApp.exe",
        module_name="demo.dll",
        module_path="C:\\Users\\Demo\\demo.dll",
        exception_code="0xc0000005",
        exception_symbol="STATUS_ACCESS_VIOLATION",
        category="MEMORY_VIOLATION",
        category_label="การจัดการหน่วยความจำ (Memory)",
        severity="CRITICAL",
        exception_meaning="พบการเข้าถึงหน่วยความจำที่ไม่ถูกต้อง",
        offline_checks=["ตรวจสอบไฟล์ระบบ", "อัปเดตโปรแกรม"],
        fault_offset="0x1234",
        process_id="0x123",
        report_id="secret-report-id",
    )


@pytest.fixture
def hang_xml() -> str:
    return """
    <Event xmlns=\"http://schemas.microsoft.com/win/2004/08/events/event\">
      <System><EventID>1002</EventID><EventRecordID>77</EventRecordID>
      <TimeCreated SystemTime=\"2026-09-18T08:00:00.000Z\" /></System>
      <EventData>
        <Data Name=\"AppName\">FrozenApp.exe</Data>
        <Data Name=\"AppVersion\">2.0.0</Data>
        <Data Name=\"ProcessId\">0x99</Data>
        <Data Name=\"ExeFileName\">C:\\Apps\\FrozenApp.exe</Data>
        <Data Name=\"ReportId\">report</Data>
        <Data Name=\"HangType\">Top level window is idle</Data>
      </EventData>
    </Event>
    """


@pytest.fixture
def crash_xml() -> str:
    return """
    <Event xmlns=\"http://schemas.microsoft.com/win/2004/08/events/event\">
      <System><EventID>1000</EventID><EventRecordID>88</EventRecordID>
      <TimeCreated SystemTime=\"2026-09-18T08:01:00.000Z\" /></System>
      <EventData>
        <Data Name=\"AppName\">CrashApp.exe</Data>
        <Data Name=\"AppVersion\">1.0.0</Data>
        <Data Name=\"ModuleName\">crash.dll</Data>
        <Data Name=\"ModuleVersion\">1.0.0</Data>
        <Data Name=\"ExceptionCode\">0xc0000005</Data>
        <Data Name=\"FaultingOffset\">1234</Data>
        <Data Name=\"ProcessId\">0x10</Data>
        <Data Name=\"AppPath\">C:\\Apps\\CrashApp.exe</Data>
        <Data Name=\"ModulePath\">C:\\Apps\\crash.dll</Data>
        <Data Name=\"IntegratorReportId\">report</Data>
      </EventData>
    </Event>
    """
