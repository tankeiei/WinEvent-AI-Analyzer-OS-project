from backend.ai_engine.gemini_analyzer import DiagnosisService
from backend.ai_engine.prompts import build_safe_telemetry
from backend.config import Settings
from backend.database import DiagnosisCache


def test_sqlite_cache_round_trip(tmp_path):
    cache = DiagnosisCache(tmp_path / "cache.db")
    payload = {"simple_summary": "summary"}
    assert cache.put("sig", "model", "v1", payload)
    assert cache.get("sig", "model", "v1")["diagnosis"] == payload
    assert cache.get("sig", "model", "v2") is None


def test_offline_diagnosis_without_api_key(tmp_path, crash_event):
    settings = Settings()
    settings.gemini_api_key = ""
    settings.cache_db_path = tmp_path / "cache.db"
    service = DiagnosisService(settings=settings, cache=DiagnosisCache(settings.cache_db_path))
    response = service.diagnose(crash_event)
    assert response.source == "offline"
    assert response.diagnosis.probable_causes
    assert response.diagnosis.actionable_resolutions
    assert response.warning


def test_gemini_projection_redacts_machine_specific_fields(crash_event):
    projected = build_safe_telemetry(crash_event)
    assert "app_path" not in projected
    assert "module_path" not in projected
    assert "process_id" not in projected
    assert "report_id" not in projected
    assert projected["exception_code"] == crash_event.exception_code


def test_gemini_result_is_cached(monkeypatch, tmp_path, crash_event):
    settings = Settings()
    settings.gemini_api_key = "configured"
    settings.cache_db_path = tmp_path / "cache.db"
    cache = DiagnosisCache(settings.cache_db_path)

    class FakeAnalyzer:
        enabled = True
        calls = 0

        def analyze(self, event):
            self.calls += 1
            from backend.ai_engine.offline import build_offline_diagnosis
            return build_offline_diagnosis(event)

    analyzer = FakeAnalyzer()
    service = DiagnosisService(settings=settings, cache=cache, analyzer=analyzer)
    first = service.diagnose(crash_event)
    second = service.diagnose(crash_event)
    assert first.source == "gemini"
    assert second.source == "cache"
    assert analyzer.calls == 1
