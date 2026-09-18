"""Safe Crash and Hang Simulator for WinEvent Analyzer.

This tool safely simulates specific Windows application crashes (Event ID 1000)
and application freezes/hangs (Event ID 1002) in an isolated child process.
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
        "event_id": 1000,
        "type": "CRASH",
        "code": "0xc0000409",
        "symbol": "STATUS_STACK_BUFFER_OVERRUN",
        "description": "Calling the Windows Universal C Runtime abort() to trigger a real Application Error event",
        "cmd": [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Add-Type @\"\nusing System;\nusing System.Runtime.InteropServices;\npublic static class NativeAbort {\n    [DllImport(\"ucrtbase.dll\", CallingConvention=CallingConvention.Cdecl)]\n    public static extern void abort();\n}\n\"@; [NativeAbort]::abort()"
        ]
    },
    "access_violation": {
        "event_id": 1000,
        "type": "CRASH",
        "code": "0xc0000005",
        "symbol": "STATUS_ACCESS_VIOLATION",
        "description": "Raising a native access violation in an isolated PowerShell child process",
        "cmd": [
            "powershell", "-NoProfile", "-NonInteractive", "-Command",
            "Add-Type -TypeDefinition 'using System;using System.Runtime.InteropServices;public static class NativeAccessViolation{[DllImport(\"kernel32.dll\")] public static extern void RaiseException(uint code,uint flags,uint arguments,IntPtr argumentList);}'; [NativeAccessViolation]::RaiseException(3221225477, 0, 0, [IntPtr]::Zero)"
        ]
    },
    "fail_fast": {
        "event_id": 1000,
        "type": "CRASH",
        "code": "0x80131623",
        "symbol": "COR_E_FAILFAST",
        "description": "Calling .NET Environment.FailFast() in an isolated PowerShell process",
        "cmd": ["powershell", "-NoProfile", "-Command", "[System.Environment]::FailFast('Crash simulation test')"]
    },
    "breakpoint": {
        "event_id": 1000,
        "type": "CRASH",
        "code": "0x80000003",
        "symbol": "STATUS_BREAKPOINT",
        "description": "Triggering debugger breakpoint in an isolated PowerShell child process",
        "cmd": ["powershell", "-NoProfile", "-Command", "[System.Diagnostics.Debugger]::Break()"]
    },
    "gui_freeze": {
        "event_id": 1002,
        "type": "HANG",
        "code": "N/A",
        "symbol": "APPLICATION_HANG",
        "description": "Creating a GUI Window that freezes its Message Loop to demonstrate Windows Hang detection",
        "cmd": [
            sys.executable, "-c",
            "import tkinter as tk, time; root = tk.Tk(); root.title('Simulated Freezing App'); root.update(); time.sleep(10)"
        ]
    }
}


def simulate_event(event_name: str):
    if event_name not in SIMULATION_PAYLOADS:
        print(f"[!] Invalid simulation type: '{event_name}'")
        print(f"    Available types: {', '.join(SIMULATION_PAYLOADS.keys())}")
        sys.exit(1)

    payload = SIMULATION_PAYLOADS[event_name]
    print("=" * 68)
    print(f"  WinEvent Analyzer - Safe {payload['type']} Simulator (Event {payload['event_id']})")
    print("=" * 68)
    print(f"[*] Target Name  : {event_name}")
    print(f"[*] Event Type   : {payload['type']} (Event ID {payload['event_id']})")
    print(f"[*] Code/Symbol  : {payload['code']} ({payload['symbol']})")
    print(f"[*] Description  : {payload['description']}")
    print("[*] Spawning isolated child process...")

    process = subprocess.Popen(payload["cmd"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    process.communicate()
    exit_code = process.returncode
    hex_exit = hex(exit_code & 0xFFFFFFFF) if exit_code is not None else "0"

    print(f"[+] Child process finished with exit code: {exit_code} ({hex_exit})")
    print("[*] Waiting 3 seconds for Windows to update Event Viewer...")
    time.sleep(3)
    print("[+] Done! You can now run 'python scripts/test_extractor.py' to inspect the event.")
    print("=" * 68)


def main():
    parser = argparse.ArgumentParser(description="Safely simulate application crashes and hangs for testing.")
    parser.add_argument(
        "--type",
        choices=list(SIMULATION_PAYLOADS.keys()),
        default="fatal_exit",
        help="Type of event to simulate (default: fatal_exit)"
    )
    args = parser.parse_args()
    simulate_event(args.type)


if __name__ == "__main__":
    main()
