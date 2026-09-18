from scripts.crash_simulator import SIMULATION_PAYLOADS


def test_fatal_exit_uses_windows_universal_c_runtime_abort():
    command = SIMULATION_PAYLOADS["fatal_exit"]["cmd"]
    assert command[0].lower() == "powershell"
    assert "ucrtbase.dll" in command[-1]
    assert "[NativeAbort]::abort()" in command[-1]


def test_access_violation_uses_isolated_native_exception():
    command = SIMULATION_PAYLOADS["access_violation"]["cmd"]
    assert command[0].lower() == "powershell"
    assert command[2] == "-NonInteractive"
    assert "RaiseException" in command[-1]
    assert "3221225477" in command[-1]


def test_simulation_allowlist_contains_supported_demo_types():
    assert set(SIMULATION_PAYLOADS) == {
        "fatal_exit",
        "access_violation",
        "fail_fast",
        "breakpoint",
        "gui_freeze",
    }
