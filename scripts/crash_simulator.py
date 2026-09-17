"""Safe Crash Simulator for WinEvent AI Analyzer.

This tool safely simulates specific Windows application crashes in an isolated
child process to test Windows Event Log extraction without impacting the system.
"""

import sys
import time
import argparse
import subprocess

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


SIMULATION_PAYLOADS = {
    "fatal_exit": {
        "code": "0x40000015",
        "symbol": "STATUS_FATAL_APP_EXIT",
        "description": "Calling C-runtime abort() inside Python to trigger emergency app termination",
        "cmd": [sys.executable, "-c", "import ctypes; ctypes.cdll.msvcrt.abort()"]
    },
    "fail_fast": {
        "code": "0x80131623",
        "symbol": "COR_E_FAILFAST",
        "description": "Calling .NET Environment.FailFast() in an isolated PowerShell process",
        "cmd": ["powershell", "-NoProfile", "-Command", "[System.Environment]::FailFast('Crash simulation test')"]
    },
    "breakpoint": {
        "code": "0x80000003",
        "symbol": "STATUS_BREAKPOINT",
        "description": "Triggering debugger breakpoint in an isolated PowerShell child process",
        "cmd": ["powershell", "-NoProfile", "-Command", "[System.Diagnostics.Debugger]::Break()"]
    }
}


def simulate_crash(crash_type: str):
    if crash_type not in SIMULATION_PAYLOADS:
        print(f"[!] Invalid crash type: '{crash_type}'")
        print(f"    Available types: {', '.join(SIMULATION_PAYLOADS.keys())}")
        sys.exit(1)

    payload = SIMULATION_PAYLOADS[crash_type]
    print("=" * 65)
    print("  WinEvent AI Analyzer - Safe Crash Simulator")
    print("=" * 65)
    print(f"[*] Target Type  : {crash_type}")
    print(f"[*] Expected Code: {payload['code']} ({payload['symbol']})")
    print(f"[*] Description  : {payload['description']}")
    print("[*] Spawning isolated child process...")

    # Run the crash snippet in a separate isolated child process
    process = subprocess.Popen(payload["cmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    # Wait for child process termination
    process.communicate()
    exit_code = process.returncode
    hex_exit = hex(exit_code & 0xFFFFFFFF)

    print(f"[+] Child process terminated with exit code: {exit_code} ({hex_exit})")
    print("[*] Waiting 3 seconds for Windows Error Reporting (WER) to write Event ID 1000...")
    time.sleep(3)
    print("[+] Done! You can now run 'python scripts/test_extractor.py' to inspect the event.")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(description="Safely simulate application crashes for testing.")
    parser.add_argument(
        "--type",
        choices=list(SIMULATION_PAYLOADS.keys()),
        default="fatal_exit",
        help="Type of crash to simulate (default: fatal_exit)"
    )
    args = parser.parse_args()
    simulate_crash(args.type)


if __name__ == "__main__":
    main()
