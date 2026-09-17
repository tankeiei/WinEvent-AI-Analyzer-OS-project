"""System prompts and structured schemas for Google Gemini AI Engine."""

from backend.models import CrashEvent

SYSTEM_DIAGNOSIS_PROMPT = """You are a Senior Windows Systems and Reliability Diagnostics Engineer analyzing Windows Application Crash and Hang events (Event IDs 1000, 1001, 1002).

YOUR ROLE:
1. Translate low-level OS telemetry (NTSTATUS Exception Codes, Memory Fault Offsets, Faulting DLLs, Hang Types) into crystal-clear Thai explanations.
2. CRITICAL PRINCIPLE: Do NOT claim definitive root cause. User-mode Windows Event Logs provide evidence of the failure boundary, not exhaustive stack traces. Always frame findings as "Possible Causes / Suggested Diagnosis" (สาเหตุที่เป็นไปได้ / ข้อสันนิษฐาน) with estimated likelihood (HIGH, MEDIUM, LOW).
3. Provide an actionable, multi-tier checklist ordered from easiest/quickest to advanced (Tier 1: Quick Fix, Tier 2: System Health, Tier 3: Advanced).

OUTPUT SCHEMA:
Return strictly a valid JSON object with the following fields:
{
  "simple_summary": "สรุปอาการสั้นๆ ใน 1-2 ประโยคเป็นภาษาไทย",
  "technical_explanation": "คำอธิบายเชิงลึกแบบ Tech-to-Human เชื่อมโยงรหัส OS Telemetry เข้ากับพฤติกรรมของโปรแกรม",
  "probable_causes": [
    {
      "cause": "หัวข้อสาเหตุที่เป็นไปได้",
      "likelihood": "HIGH" | "MEDIUM" | "LOW",
      "reasoning": "เหตุผลทางเทคนิคที่รองรับข้อสันนิษฐานนี้"
    }
  ],
  "actionable_resolutions": [
    {
      "tier": "Tier 1: Quick Fix" | "Tier 2: System Health" | "Tier 3: Advanced",
      "title": "ชื่อขั้นตอนการตรวจสอบหรือแก้ไข",
      "steps": ["ข้อ 1...", "ข้อ 2..."],
      "command": "คำสั่ง command prompt หรือ powershell (ถ้ามี หรือ null)"
    }
  ],
  "search_queries": [
    "คำค้นหาแนะนำสำหรับ Microsoft Learn หรือ StackOverflow"
  ]
}
"""


def build_event_telemetry_prompt(event: CrashEvent) -> str:
    """Builds a structured prompt for the Gemini AI model containing all event telemetry."""
    if event.event_type == "HANG":
        return f"""วิเคราะห์เหตุการณ์ Application Hang (Event ID 1002):
- Application Name: {event.app_name}
- Application Version: {event.app_version or 'N/A'}
- Executable Path: {event.app_path or 'N/A'}
- Hang Classification: {event.hang_type or 'Top level window is idle'}
- Process ID: {event.process_id or 'N/A'}
- Timestamp: {event.time_created}
- Diagnostic Category: {event.category} ({event.category_label})
- Assessed Severity: {event.severity}

โปรดวิเคราะห์ว่าเหตุใดหน้าต่างโปรแกรมจึงหยุดตอบสนองต่อ Windows Message Loop พร้อมเสนอข้อสันนิษฐานและแนวทางตรวจสอบแก้ไขตามโครงสร้าง JSON ที่กำหนด"""

    return f"""วิเคราะห์เหตุการณ์ Application Crash (Event ID {event.event_id}):
- Application Name: {event.app_name}
- Application Version: {event.app_version or 'N/A'}
- Application Path: {event.app_path or 'N/A'}
- Faulting Module: {event.module_name or 'N/A'}
- Faulting Module Path: {event.module_path or 'N/A'}
- Exception Code: {event.exception_code} ({event.exception_symbol or 'UNKNOWN'})
- Memory Fault Offset: {event.fault_offset or 'N/A'}
- Process ID: {event.process_id or 'N/A'}
- Timestamp: {event.time_created}
- Diagnostic Category: {event.category} ({event.category_label})
- Assessed Severity: {event.severity}
- Offline Diagnostic: {event.exception_meaning or 'N/A'}

โปรดวิเคราะห์ข้อผิดพลาดระดับ OS นี้ แปลงเป็นภาษาที่เข้าใจง่าย พร้อมระบุ Possible Causes และขั้นตอนการตรวจสอบแก้ไขตามโครงสร้าง JSON ที่กำหนด"""
