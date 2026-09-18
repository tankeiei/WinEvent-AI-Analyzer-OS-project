from backend.extractor.parser import parse_event_xml


def test_parse_crash_event(crash_xml):
    event = parse_event_xml(crash_xml)
    assert event is not None
    assert event.event_id == 1000
    assert event.event_type == "CRASH"
    assert event.app_name == "CrashApp.exe"
    assert event.exception_symbol == "STATUS_ACCESS_VIOLATION"
    assert event.fault_offset == "0x1234"
    assert event.signature_hash
    assert "signature_hash" in event.model_dump()


def test_parse_hang_event(hang_xml):
    event = parse_event_xml(hang_xml)
    assert event is not None
    assert event.event_id == 1002
    assert event.event_type == "HANG"
    assert event.app_name == "FrozenApp.exe"
    assert event.hang_type == "Top level window is idle"
    assert event.exception_code == "N/A"


def test_parse_invalid_xml_returns_none():
    assert parse_event_xml("<not-valid") is None
    assert parse_event_xml("") is None


def test_parse_event_with_missing_data_uses_safe_defaults():
    xml = """<Event><System><EventID>1000</EventID></System><EventData /></Event>"""
    event = parse_event_xml(xml)
    assert event is not None
    assert event.app_name == "UnknownApp.exe"
    assert event.exception_code == "0x00000000"
