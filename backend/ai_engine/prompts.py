"""Prompts and privacy-safe telemetry projection for diagnosis."""

from backend.models import CrashEvent


PROMPT_VERSION = "v1"

SYSTEM_DIAGNOSIS_PROMPT = """
You are a Senior Windows Systems and Reliability Diagnostics Engineer.
Analyze Windows Application Crash and Hang telemetry and answer in Thai.

Rules:
1. Treat the data as evidence of a failure boundary, never as proof of a definitive root cause.
2. Use the wording Possible Causes / Suggested Diagnosis and assign HIGH, MEDIUM, or LOW likelihood.
3. Return practical troubleshooting steps in three tiers: Tier 1: Quick Fix, Tier 2: System Health, Tier 3: Advanced.
4. Never tell the user that you executed a command. Commands are suggestions only.
5. Follow the provided structured response schema exactly.
""".strip()


def build_safe_telemetry(event: CrashEvent) -> dict:
    """Return only fields needed for diagnosis; omit paths, IDs and host data."""
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "app_name": event.app_name,
        "module_name": event.module_name,
        "exception_code": event.exception_code,
        "exception_symbol": event.exception_symbol,
        "category": event.category,
        "category_label": event.category_label,
        "severity": event.severity,
        "hang_type": event.hang_type,
        "fault_offset": event.fault_offset,
        "offline_diagnostic": event.exception_meaning,
    }


def build_event_telemetry_prompt(event: CrashEvent) -> str:
    telemetry = build_safe_telemetry(event)
    return (
        "วิเคราะห์ OS telemetry ต่อไปนี้และสรุปเป็นภาษาไทย โดยห้ามยืนยัน root cause "
        "ให้ระบุ Possible Causes และ Suggested Diagnosis ตามข้อมูลที่มีเท่านั้น:\n\n"
        f"{telemetry}"
    )
