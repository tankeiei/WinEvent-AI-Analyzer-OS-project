from backend.extractor import event_reader


def test_native_reader_is_used_when_success(monkeypatch, crash_event):
    monkeypatch.setattr(event_reader, "HAS_PYWIN32", True)
    monkeypatch.setattr(event_reader, "_fetch_via_pywin32", lambda *args: ([crash_event], None))
    result = event_reader.read_event_log(hours=24, max_events=5)
    assert result.events == [crash_event]
    assert result.metadata.engine_used == "pywin32"
    assert result.metadata.fallback_reason is None


def test_native_failure_falls_back_to_powershell(monkeypatch, crash_event):
    monkeypatch.setattr(event_reader, "HAS_PYWIN32", True)
    monkeypatch.setattr(event_reader, "_fetch_via_pywin32", lambda *args: ([], "native failed"))
    monkeypatch.setattr(event_reader, "_fetch_via_powershell", lambda *args: ([crash_event], None))
    result = event_reader.read_event_log(hours=24, max_events=5)
    assert result.metadata.engine_used == "powershell"
    assert result.metadata.fallback_reason == "native failed"


def test_both_engines_unavailable(monkeypatch):
    monkeypatch.setattr(event_reader, "HAS_PYWIN32", False)
    monkeypatch.setattr(event_reader, "_fetch_via_powershell", lambda *args: ([], "powershell failed"))
    result = event_reader.read_event_log(hours=24, max_events=5)
    assert result.events == []
    assert result.metadata.engine_used == "unavailable"
