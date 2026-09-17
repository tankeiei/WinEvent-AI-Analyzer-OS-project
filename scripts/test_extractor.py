"""CLI Test script for WinEvent AI Analyzer (Phase 1 OS Extraction)."""

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


def run_test(hours: int = 48, limit: int = 10, app: str = None):
    print("=" * 80)
    print("  WinEvent AI Analyzer - Phase 1 OS Extraction Test")
    print("=" * 80)
    print(f"[*] Engine Mode : {'pywin32 (Native C-API)' if HAS_PYWIN32 else 'PowerShell Fallback'}")
    print(f"[*] Time Window : Last {hours} hours")
    print(f"[*] Max Limit   : {limit} events")
    if app:
        print(f"[*] Filter App  : {app}")
    print("[*] Querying Windows Event Log (Channel: Application, EventID: 1000)...")
    print("-" * 80)

    events = get_crash_events(hours=hours, max_events=limit, app_name=app)

    if not events:
        print("[!] No crash events found within the specified time window.")
        print("    Tip: Try increasing --hours (e.g. --hours 168 for 7 days)")
        print("    Or run: python scripts/crash_simulator.py --type access_violation")
        print("=" * 80)
        return

    print(f"[+] Successfully extracted {len(events)} crash event(s)!\n")

    # Display Table
    header = f"{'#':<3} | {'Timestamp':<20} | {'Application':<20} | {'Module':<18} | {'Code':<12} | {'Symbol'}"
    print(header)
    print("-" * len(header))

    for idx, e in enumerate(events, 1):
        # Format time
        time_str = e.time_created[:19].replace("T", " ") if e.time_created else "N/A"
        app_disp = (e.app_name[:18] + "..") if len(e.app_name) > 20 else e.app_name
        mod_disp = (e.module_name[:16] + "..") if len(e.module_name) > 18 else e.module_name
        symbol_disp = e.exception_symbol or "UNKNOWN"
        print(f"{idx:<3} | {time_str:<20} | {app_disp:<20} | {mod_disp:<18} | {e.exception_code:<12} | {symbol_disp}")

    print("\n" + "=" * 80)
    print("  Detailed View of the Latest Event (Normalized Data Model):")
    print("=" * 80)
    latest = events[0]
    print(json.dumps(latest.model_dump(), indent=2, ensure_ascii=False))

    print("\n" + "-" * 80)
    print(f"[*] Human Explanation: {latest.exception_meaning}")
    print(f"[*] Signature Hash    : {latest.signature_hash}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Phase 1 OS Log Extractor")
    parser.add_argument("--hours", type=int, default=48, help="Hours lookback (default: 48)")
    parser.add_argument("--limit", type=int, default=10, help="Max results (default: 10)")
    parser.add_argument("--app", type=str, default=None, help="Filter by application name")
    args = parser.parse_args()
    run_test(hours=args.hours, limit=args.limit, app=args.app)
