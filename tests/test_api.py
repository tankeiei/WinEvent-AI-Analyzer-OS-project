from fastapi.testclient import TestClient

from backend import app as app_module
from backend.ai_engine.gemini_analyzer import DiagnosisService
from backend.config import Settings
from backend.database import DiagnosisCache
from backend.extractor.event_reader import EventReadResult
from backend.models import ExtractionMetadata


def test_dashboard_and_static_page(monkeypatch, crash_event):
    result = EventReadResult(
        events=[crash_event],
        metadata=ExtractionMetadata(engine_used="pywin32", native_available=True),
    )
    monkeypatch.setattr(app_module, "read_event_log", lambda *args: result)
    client = TestClient(app_module.app)
    dashboard = client.get("/api/dashboard?hours=24&limit=10")
    assert dashboard.status_code == 200
    assert dashboard.json()["extractor"]["engine_used"] == "pywin32"
    assert dashboard.json()["events"][0]["signature_hash"] == crash_event.signature_hash
    assert client.get("/").status_code == 200


def test_analyze_endpoint_works_without_api_key(monkeypatch, tmp_path, crash_event):
    settings = Settings()
    settings.gemini_api_key = ""
    settings.cache_db_path = tmp_path / "cache.db"
    old_service = app_module.diagnosis_service
    app_module.diagnosis_service = DiagnosisService(
        settings=settings, cache=DiagnosisCache(settings.cache_db_path)
    )
    try:
        client = TestClient(app_module.app)
        response = client.post("/api/analyze", json={"event": crash_event.model_dump()})
        assert response.status_code == 200
        assert response.json()["source"] == "offline"
        assert response.json()["diagnosis"]["simple_summary"]
    finally:
        app_module.diagnosis_service = old_service


def test_simulator_rejects_arbitrary_commands():
    client = TestClient(app_module.app)
    response = client.post("/api/simulate", json={"simulation_type": "format_c_drive"})
    assert response.status_code == 422


def test_gui_hang_demo_fallback_is_visible_in_dashboard(monkeypatch, crash_event):
    result = EventReadResult(
        events=[crash_event],
        metadata=ExtractionMetadata(engine_used="pywin32", native_available=True),
    )
    monkeypatch.setattr(app_module, "read_event_log", lambda *args: result)
    app_module._simulation_events.clear()
    app_module._simulation_events.append(app_module._build_simulation_event("gui_freeze"))
    try:
        client = TestClient(app_module.app)
        response = client.get("/api/dashboard?hours=24&limit=10&type=HANG")
        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) == 1
        assert events[0]["event_id"] == 1002
        assert events[0]["report_id"] == "SIMULATION:gui_freeze"
    finally:
        app_module._simulation_events.clear()


def test_access_violation_demo_uses_matching_diagnosis():
    event = app_module._build_simulation_event("access_violation")
    assert event.event_id == 1000
    assert event.exception_code == "0xc0000005"
    assert event.exception_symbol == "STATUS_ACCESS_VIOLATION"
    assert event.category == "MEMORY_VIOLATION"
    assert event.severity == "CRITICAL"
    assert event.report_id == "SIMULATION:access_violation"
