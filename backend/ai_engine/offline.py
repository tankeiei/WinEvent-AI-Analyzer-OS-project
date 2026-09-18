"""Deterministic diagnosis used when Gemini is unavailable."""

from backend.models import (
    AIDiagnosisResult,
    CauseHypothesis,
    CrashEvent,
    ResolutionAction,
)


def build_offline_diagnosis(event: CrashEvent) -> AIDiagnosisResult:
    meaning = event.exception_meaning or "ยังไม่มีคำอธิบายเฉพาะสำหรับเหตุการณ์นี้"
    event_label = "โปรแกรมแครช" if event.event_type == "CRASH" else "โปรแกรมค้าง"
    identifier = event.exception_code or event.hang_type or event.category

    causes = [
        CauseHypothesis(
            cause=event.category_label or event.category,
            likelihood="MEDIUM",
            reasoning=(
                f"Windows บันทึก {event_label} ของ {event.app_name} "
                f"โดยพบข้อมูล {identifier}; ข้อมูล Event Log ยังไม่ใช่ call stack เต็มรูปแบบ"
            ),
        )
    ]

    checks = event.offline_checks or [
        "ตรวจสอบการอัปเดตของโปรแกรมและไดรเวอร์ที่เกี่ยวข้อง",
        "ทำซ้ำปัญหาโดยปิดปลั๊กอินหรือโปรแกรมเสริมที่ไม่จำเป็น",
        "เก็บ Event Log เพิ่มเติมก่อนสรุปสาเหตุสุดท้าย",
    ]
    resolutions = []
    tier_names = [
        "Tier 1: Quick Fix",
        "Tier 2: System Health",
        "Tier 3: Advanced",
    ]
    for index, check in enumerate(checks):
        tier = tier_names[min(index, len(tier_names) - 1)]
        resolutions.append(
            ResolutionAction(
                tier=tier,
                title="ตรวจสอบตามคำแนะนำ Offline",
                steps=[check],
                command=None,
            )
        )

    query = " ".join(
        value
        for value in [event.app_name, event.module_name, event.exception_code]
        if value and value != "N/A"
    )
    return AIDiagnosisResult(
        simple_summary=f"{event.app_name} พบเหตุการณ์ {event_label} จาก Windows Event Log",
        technical_explanation=meaning,
        probable_causes=causes,
        actionable_resolutions=resolutions,
        search_queries=[query or "Windows application crash Event Viewer"],
    )
