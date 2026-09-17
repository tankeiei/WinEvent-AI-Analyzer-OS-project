"""CLI Test script for WinEvent Analyzer (Phase 1 OS Extraction)."""

import sys
import os
import json
import argparse

# Add parent directory to sys.path so we can import backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from backend.extractor.event_reader import get_crash_events, HAS_PYWIN32


def run_test(hours: int = 48, limit: int = 10, event_type: str = "ALL", app: str = None):
    print("=" * 86)
    print("  WinEvent Analyzer - Phase 1 OS Extraction Test (Crash & Hang)")
    print("=" * 86)
    print(f"[*] Engine Mode : {'pywin32 (Native C-API)' if HAS_PYWIN32 else 'PowerShell Fallback'}")
    print(f"[*] Time Window : Last {hours} hours")
    print(f"[*] Event Filter: {event_type} (ID 1000/1001/1002)")
    print(f"[*] Max Limit   : {limit} events")
    if app:
        print(f"[*] Filter App  : {app}")
    print("[*] Querying Windows Event Log (Channel: Application)...")
    print("-" * 86)

    events = get_crash_events(hours=hours, max_events=limit, event_type=event_type, app_name=app)

    if not events:
        print("[!] No events found within the specified time window.")
        print("    Tip: Try increasing --hours (e.g. --hours 720 for 30 days)")
        print("    Or simulate with: python scripts/crash_simulator.py --type fatal_exit")
        print("=" * 86)
        return

    print(f"[+] Successfully extracted {len(events)} event(s)!\n")

    # Display Table with Type Column
    header = f"{'#':<3} | {'Type':<5} | {'Timestamp':<19} | {'Application':<20} | {'Code/Detail':<14} | {'Symbol'}"
    print(header)
    print("-" * len(header))

    for idx, e in enumerate(events, 1):
        time_str = e.time_created[:19].replace("T", " ") if e.time_created else "N/A"
        app_disp = (e.app_name[:18] + "..") if len(e.app_name) > 20 else e.app_name
        detail_disp = e.exception_code if e.event_type == "CRASH" else (e.hang_type or "HANG")[:13]
        symbol_disp = e.exception_symbol or "UNKNOWN"
        print(f"{idx:<3} | {e.event_type:<5} | {time_str:<19} | {app_disp:<20} | {detail_disp:<14} | {symbol_disp}")

    print("\n" + "=" * 86)
    print("  Detailed View of the Latest Event (Normalized Data Model):")
    print("=" * 86)
    latest = events[0]
    print(json.dumps(latest.model_dump(), indent=2, ensure_ascii=False))

    print("\n" + "-" * 86)
    print(f"[*] Explanation: {latest.exception_meaning}")
    print(f"[*] Signature  : {latest.signature_hash}")
    print("=" * 86)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Phase 1 OS Log Extractor")
    parser.add_argument("--hours", type=int, default=48, help="Hours lookback (default: 48)")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--type", choices=["ALL", "CRASH", "HANG"], default="ALL", help="Event type filter")
    parser.add_argument("--app", type=str, default=None, help="Filter by application name")
    args = parser.parse_args()
    run_test(hours=args.hours, limit=args.limit, event_type=args.type, app=args.app)
