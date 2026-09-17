"""Extractor package for reading and parsing Windows Event Logs."""

from backend.extractor.event_reader import get_crash_events

__all__ = ["get_crash_events"]
