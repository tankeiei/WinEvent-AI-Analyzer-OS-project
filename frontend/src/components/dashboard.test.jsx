import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardApp from "./dashboard";
import { analyzeEvent, getDashboard, getSystemInfo, simulateEvent } from "../api";

vi.mock("../api", () => ({
  getSystemInfo: vi.fn(),
  getDashboard: vi.fn(),
  analyzeEvent: vi.fn(),
  simulateEvent: vi.fn(),
}));

const event = {
  event_id: 1000,
  event_type: "CRASH",
  record_id: 11,
  time_created: "2026-09-18T10:00:00Z",
  app_name: "demo.exe",
  module_name: "demo.dll",
  exception_code: "0xc0000005",
  category: "MEMORY_VIOLATION",
  category_label: "Memory / Access Violation",
  severity: "HIGH",
  exception_meaning: "Access violation",
  offline_checks: ["ตรวจสอบ module"],
  signature_hash: "signature-1",
};

beforeEach(() => {
  vi.clearAllMocks();
  getSystemInfo.mockResolvedValue({ app_version: "3.0.0", machine_name: "TEST-PC", ai_configured: false });
  getDashboard.mockResolvedValue({
    events: [event],
    stats: { total_events: 1, total_crashes: 1, total_hangs: 0, total_critical: 0, total_high: 1, top_failing_app: "demo.exe", top_apps: [{ name: "demo.exe", count: 1 }] },
    extractor: { engine_used: "pywin32", duration_ms: 2 },
    scanned_at: "2026-09-18T10:01:00Z",
  });
  analyzeEvent.mockResolvedValue({ signature_hash: "signature-1", source: "offline", model: null, warning: "Offline mode", diagnosis: { simple_summary: "ตรวจพบ access violation", technical_explanation: "ต้องตรวจสอบ module", probable_causes: [], actionable_resolutions: [], search_queries: [] } });
});

describe("Mission Control dashboard", () => {
  it("renders a real event and opens its investigation workspace", async () => {
    render(<DashboardApp />);
    expect((await screen.findAllByText("demo.exe")).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("0xc0000005")).toBeInTheDocument();
    expect(screen.getByText("Offline mode")).toBeInTheDocument();
    expect(screen.getByText("Access violation")).toBeInTheDocument();
  });

  it("opens the command menu with Ctrl+K and can trigger a scan", async () => {
    render(<DashboardApp />);
    await screen.findAllByText("demo.exe");
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(await screen.findByPlaceholderText("ค้นหา incident หรือ action...")).toBeInTheDocument();
    fireEvent.click(screen.getByText("สแกน Event Log ใหม่"));
    await waitFor(() => expect(getDashboard).toHaveBeenCalled());
  });

  it("keeps analysis keyed by signature and renders offline source", async () => {
    render(<DashboardApp />);
    await screen.findAllByText("demo.exe");
    fireEvent.click(screen.getByRole("button", { name: /วิเคราะห์/ }));
    expect(await screen.findByText("ตรวจพบ access violation")).toBeInTheDocument();
    expect(analyzeEvent).toHaveBeenCalledWith(event, false);
  });

  it("shows data-backed KPI ratios and switches a dense incident feed to compact mode", async () => {
    const denseEvents = Array.from({ length: 12 }, (_, index) => ({
      ...event,
      record_id: index + 1,
      app_name: `demo-${index}.exe`,
      time_created: index < 6 ? "2026-09-18T10:00:00Z" : "2026-09-17T10:00:00Z",
    }));
    getDashboard.mockResolvedValueOnce({
      events: denseEvents,
      stats: { total_events: 12, total_crashes: 12, total_hangs: 0, total_critical: 0, total_high: 12, top_failing_app: "demo-0.exe", top_apps: [] },
      extractor: { engine_used: "pywin32", duration_ms: 2 },
      scanned_at: "2026-09-18T10:01:00Z",
    });

    render(<DashboardApp />);
    expect((await screen.findAllByText("100% of total")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Compact" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Compact" }));
    expect(screen.getByRole("button", { name: /demo-0\.exe/ })).toHaveAttribute("aria-current", "true");
  });
});
