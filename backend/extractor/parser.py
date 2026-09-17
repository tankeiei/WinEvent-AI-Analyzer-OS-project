"""Parser module for converting Windows Event XML into CrashEvent models."""

import re
import xml.etree.ElementTree as ET
from typing import Optional, Dict, Any

from backend.models import CrashEvent
from backend.extractor.error_codes import normalize_code, lookup_exception


def parse_event_xml(xml_str: str) -> Optional[CrashEvent]:
    """
    Parses a single Windows Event XML string into a CrashEvent instance.
    Supports:
      - Event ID 1000/1001: Application Error (Crash)
      - Event ID 1002: Application Hang (Window/Process Freeze)
    """
    if not xml_str or not xml_str.strip():
        return None

    try:
        # Strip default XML namespace for simpler XPath querying
        clean_xml = re.sub(r'\sxmlns="[^"]+"', '', xml_str, count=1)
        clean_xml = re.sub(r"\sxmlns='[^']+'", '', clean_xml, count=1)
        root = ET.fromstring(clean_xml)
    except ET.ParseError:
        return None

    # Extract System info
    system = root.find("System")
    if system is None:
        return None

    event_id_elem = system.find("EventID")
    event_id = int(event_id_elem.text) if event_id_elem is not None and event_id_elem.text else 1000

    record_id_elem = system.find("EventRecordID")
    record_id = int(record_id_elem.text) if record_id_elem is not None and record_id_elem.text else None

    time_created_elem = system.find("TimeCreated")
    time_created = ""
    if time_created_elem is not None:
        time_created = time_created_elem.attrib.get("SystemTime", "")

    # Extract EventData tags
    event_data = root.find("EventData")
    data_dict: Dict[str, str] = {}
    data_list = []

    if event_data is not None:
        for data_elem in event_data.findall("Data"):
            name = data_elem.attrib.get("Name")
            val = (data_elem.text or "").strip()
            data_list.append(val)
            if name:
                data_dict[name.lower()] = val

    def get_val(name_key: str, index: int, default: str = "") -> str:
        if name_key.lower() in data_dict:
            return data_dict[name_key.lower()]
        if 0 <= index < len(data_list):
            return data_list[index]
        return default

    # -------------------------------------------------------------
    # CASE 1: Event ID 1002 (Application Hang / Window Unresponsive)
    # -------------------------------------------------------------
    if event_id == 1002:
        app_name = get_val("AppName", 0, "UnknownApp.exe")
        app_version = get_val("AppVersion", 1, None)
        process_id = get_val("ProcessId", 2, None)
        app_path = get_val("ExeFileName", 5, None)
        report_id = get_val("ReportId", 6, None)
        hang_type = get_val("HangType", 9, "Application Unresponsive")
        
        symbol, meaning = lookup_exception("APPLICATION_HANG")

        return CrashEvent(
            event_id=1002,
            event_type="HANG",
            record_id=record_id,
            time_created=time_created,
            app_name=app_name,
            app_version=app_version,
            app_path=app_path,
            module_name="UI Message Loop / Thread",
            module_version=None,
            module_path=None,
            exception_code="N/A",
            exception_symbol=symbol,
            exception_meaning=meaning,
            hang_type=hang_type,
            fault_offset=None,
            process_id=process_id,
            report_id=report_id,
        )

    # -------------------------------------------------------------
    # CASE 2: Event ID 1000 / 1001 (Application Error / Crash)
    # -------------------------------------------------------------
    app_name = get_val("AppName", 0, "UnknownApp.exe")
    app_version = get_val("AppVersion", 1, None)
    module_name = get_val("ModuleName", 3, "UnknownModule.dll")
    module_version = get_val("ModuleVersion", 4, None)
    raw_code = get_val("ExceptionCode", 6, "0x00000000")
    fault_offset = get_val("FaultingOffset", 7, None)
    process_id = get_val("ProcessId", 8, None)
    app_path = get_val("AppPath", 10, None)
    module_path = get_val("ModulePath", 11, None)
    report_id = get_val("IntegratorReportId", 12, None)

    hex_code = normalize_code(raw_code)
    symbol, meaning = lookup_exception(hex_code)

    if fault_offset and not fault_offset.startswith("0x"):
        fault_offset = f"0x{fault_offset}"

    return CrashEvent(
        event_id=event_id,
        event_type="CRASH",
        record_id=record_id,
        time_created=time_created,
        app_name=app_name,
        app_version=app_version,
        app_path=app_path,
        module_name=module_name,
        module_version=module_version,
        module_path=module_path,
        exception_code=hex_code,
        exception_symbol=symbol,
        exception_meaning=meaning,
        hang_type=None,
        fault_offset=fault_offset,
        process_id=process_id,
        report_id=report_id,
    )
