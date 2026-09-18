import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Check,
  CircleAlert,
  ChevronRight,
  Clipboard,
  Clock3,
  Code2,
  Command,
  Copy,
  Database,
  FileJson,
  Filter,
  Gauge,
  Github,
  HardDrive,
  Info,
  LayoutDashboard,
  ListChecks,
  ListFilter,
  Menu,
  MonitorCog,
  MoreHorizontal,
  Play,
  RefreshCw,
  Search,
  ServerCog,
  Settings2,
  ShieldCheck,
  Sparkles,
  Terminal,
  TimerReset,
  TriangleAlert,
  X,
  Zap,
} from "lucide-react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { analyzeEvent, getDashboard, getSystemInfo, simulateEvent } from "../api";
import { cn, copyToClipboard, formatTime, relativeTime, severityTone, sourceLabel } from "../lib/utils";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle, Badge, Button, Card, CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, Dialog, DialogContent, DialogDescription, DialogTitle, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "./ui";

const categories = [
  ["ALL", "ทุกหมวดหมู่"],
  ["MEMORY_VIOLATION", "Memory / Access Violation"],
  ["APPLICATION_HANG", "Application Hang"],
  ["RUNTIME_FRAMEWORK", "Runtime Framework"],
  ["SECURITY_BUFFER", "Security / Buffer"],
  ["DEBUG_ASSERTION", "Debug / Assertion"],
  ["CPU_HARDWARE", "CPU / Hardware"],
];

const simulations = [
  ["fail_fast", ".NET FailFast", "จำลอง crash จาก runtime", "danger"],
  ["fatal_exit", "C-Runtime abort", "จำลอง process abort", "danger"],
  ["access_violation", "Access Violation", "จำลอง invalid memory access · 0xc0000005", "danger"],
  ["breakpoint", "DebugBreak", "จำลอง assertion / breakpoint", "warning"],
  ["gui_freeze", "GUI Hang", "จำลองหน้าต่างค้าง", "warning"],
];

function toneForSeverity(severity) {
  const tone = severityTone(severity);
  return tone === "critical" || tone === "high" ? "red" : tone === "medium" ? "amber" : "cyan";
}

function engineLabel(engine) {
  if (engine === "pywin32") return "pywin32 Native";
  if (engine === "powershell") return "PowerShell fallback";
  return "Extractor unavailable";
}

function isSimulatedEvent(event) {
  return String(event?.report_id || "").startsWith("SIMULATION:");
}

function StatCard({ icon: Icon, label, value, helper, tone = "cyan", ratio }) {
  const tones = {
    cyan: { icon: "text-cyan-200 bg-cyan-300/10 border-cyan-300/15", bar: "bg-cyan-300" },
    red: { icon: "text-rose-200 bg-rose-400/10 border-rose-300/15", bar: "bg-rose-300" },
    amber: { icon: "text-amber-100 bg-amber-400/10 border-amber-300/15", bar: "bg-amber-300" },
    violet: { icon: "text-violet-200 bg-violet-400/10 border-violet-300/15", bar: "bg-violet-300" },
  };
  const palette = tones[tone];
  return (
    <Card className="group relative overflow-hidden p-4 transition duration-200 hover:-translate-y-0.5 hover:border-slate-300/20">
      <div className={cn("absolute inset-x-0 top-0 h-px opacity-60", palette.bar)} />
      <div className="relative flex items-start justify-between gap-3">
        <div className={cn("flex h-9 w-9 items-center justify-center rounded-xl border", palette.icon)}>
          <Icon className="h-4 w-4" />
        </div>
        {ratio !== undefined && <span className="text-[10px] font-semibold tabular-nums text-slate-500">{ratio}% of total</span>}
      </div>
      <p className="relative mt-5 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400">{label}</p>
      <div className="relative mt-1 flex items-end justify-between gap-3">
        <strong className="font-mono text-3xl font-semibold tracking-tight text-white">{value}</strong>
        <span className="max-w-[58%] text-right text-[11px] leading-4 text-slate-400">{helper}</span>
      </div>
      {ratio !== undefined && <div className="mt-4 h-1 overflow-hidden rounded-full bg-white/[0.06]"><div className={cn("h-full rounded-full transition-all duration-500", palette.bar)} style={{ width: `${Math.min(100, Math.max(0, ratio))}%` }} /></div>}
    </Card>
  );
}

function Sidebar({ system, activeView, onNavigate }) {
  const nav = [
    ["dashboard", "Mission control", LayoutDashboard, "system-pulse"],
    ["events", "Event stream", Activity, "incident-feed"],
    ["diagnostics", "AI diagnostics", BrainCircuit, "investigation-workspace"],
    ["demo", "Demo Lab", Zap, "demo-lab"],
  ];
  return (
    <aside className="hidden w-[216px] shrink-0 border-r border-slate-400/10 bg-[#07101d]/80 px-3.5 py-4 lg:flex lg:flex-col">
      <div className="flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-200/20 bg-cyan-300/10 font-mono text-xs font-black tracking-wider text-cyan-200 shadow-[0_0_28px_rgba(34,211,238,.12)]">WE</div>
        <div><p className="text-sm font-semibold text-white">WinEvent</p><p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Analyzer OS</p></div>
      </div>
      <div className="mt-8 px-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">Workspace</div>
      <nav className="mt-3 space-y-1" aria-label="Main navigation">
        {nav.map(([id, label, Icon, target]) => (
          <button key={id} onClick={() => onNavigate(id, target)} className={cn("group flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-xs font-semibold transition", activeView === id ? "bg-cyan-300/10 text-cyan-100 ring-1 ring-cyan-300/15" : "text-slate-400 hover:bg-white/[0.05] hover:text-slate-100")}>
            <Icon className="h-4 w-4" /><span>{label}</span>{activeView === id && <ChevronRight className="ml-auto h-3.5 w-3.5" />}
          </button>
        ))}
      </nav>
      <div className="mt-auto space-y-3">
        <Card className="border-cyan-300/10 bg-cyan-300/[0.035] p-3 shadow-none">
          <div className="flex items-center gap-2 text-cyan-100"><ShieldCheck className="h-4 w-4" /><span className="text-xs font-semibold">Local-first telemetry</span></div>
          <p className="mt-2 text-[11px] leading-5 text-slate-500">ส่งเฉพาะข้อมูลจำเป็นไปยัง AI และเก็บ cache ไว้ในเครื่องนี้</p>
        </Card>
        <div className="flex items-center justify-between px-2 text-[10px] text-slate-600"><span>v{system?.app_version || "3.0.0"}</span><span className="flex items-center gap-1"><Github className="h-3 w-3" /> local app</span></div>
      </div>
    </aside>
  );
}

function CommandBar({ system, extractor, loading, error, onRefresh, onOpenCommand, activeView, onOpenMobileNav, scannedAt }) {
  return (
    <header className="border-b border-slate-400/10 bg-[#060b14]/82 px-4 py-4 backdrop-blur-xl sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button className="lg:hidden" aria-label="เปิดเมนู" onClick={onOpenMobileNav}><Menu className="h-5 w-5 text-cyan-200" /></button>
          <div><div className="flex items-center gap-2"><p className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-200/70">Local OS observability</p><span className="h-1 w-1 rounded-full bg-cyan-300 shadow-[0_0_10px_#67e8f9]" /></div><h1 className="mt-1 text-xl font-semibold tracking-tight text-white sm:text-2xl">{activeView === "dashboard" ? "Mission control" : activeView === "events" ? "Event stream" : activeView === "demo" ? "Demo Lab" : "AI diagnostics"}</h1><p className="mt-1 hidden text-xs text-slate-500 sm:block">Windows crash และ hang investigation console</p></div>
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <button onClick={onOpenCommand} className="hidden h-9 items-center gap-3 rounded-xl border border-white/[0.09] bg-white/[0.035] px-3 text-xs text-slate-500 transition hover:border-cyan-200/20 hover:text-slate-200 sm:flex"><Search className="h-3.5 w-3.5" />ค้นหา incident<span className="ml-2 flex items-center gap-1 rounded-md border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-slate-600"><Command className="h-2.5 w-2.5" />K</span></button>
          <div className="hidden items-center gap-2 text-right md:flex"><span className={cn("h-2 w-2 rounded-full", error ? "bg-rose-300 shadow-[0_0_13px_#fb7185]" : extractor?.engine_used === "pywin32" ? "bg-emerald-300 shadow-[0_0_13px_#6ee7b7]" : "bg-amber-300 shadow-[0_0_13px_#fcd34d]")} /><div><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400">{error ? "Unavailable" : engineLabel(extractor?.engine_used)}</p><p className="text-[11px] text-slate-400">{system?.ai_configured ? "Gemini ready" : "Offline mode"}</p></div></div>
          <Button size="sm" onClick={onRefresh} disabled={loading}><RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} /><span className="hidden sm:inline">สแกนใหม่</span></Button>
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">
        <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1", error ? "border-rose-300/20 bg-rose-400/10 text-rose-100" : "border-emerald-300/15 bg-emerald-400/5 text-emerald-200/90")}><span className={cn("h-1.5 w-1.5 rounded-full", error ? "bg-rose-300" : "bg-emerald-300")} /> {error ? "Event Log unavailable" : "Event Log connected"}</span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-400/10 bg-white/[0.025] px-2.5 py-1"><MonitorCog className="h-3 w-3" /> {system?.machine_name || "กำลังอ่าน host..."}</span>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-400/10 bg-white/[0.025] px-2.5 py-1"><Database className="h-3 w-3" /> Application channel</span>
        {scannedAt && <span className="ml-auto inline-flex items-center gap-1.5 text-slate-500"><Clock3 className="h-3 w-3" /> scanned {formatTime(scannedAt)}</span>}
      </div>
    </header>
  );
}

function MobileNavigation({ open, onOpenChange, activeView, onNavigate }) {
  const nav = [
    ["dashboard", "Mission control", LayoutDashboard, "system-pulse"],
    ["events", "Event stream", Activity, "incident-feed"],
    ["diagnostics", "AI diagnostics", BrainCircuit, "investigation-workspace"],
    ["demo", "Demo Lab", Zap, "demo-lab"],
  ];
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent className="left-0 top-0 h-full w-[min(86vw,320px)] max-w-none -translate-x-0 -translate-y-0 rounded-none rounded-r-2xl p-5"><div className="flex items-center gap-3"><div className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-200/20 bg-cyan-300/10 font-mono text-xs font-black text-cyan-200">WE</div><div><p className="text-sm font-semibold text-white">WinEvent</p><p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">Analyzer OS</p></div></div><p className="mt-9 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-600">Workspace</p><nav className="mt-3 space-y-1">{nav.map(([id, label, Icon, target]) => <button key={id} onClick={() => { onOpenChange(false); onNavigate(id, target); }} className={cn("flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-xs font-semibold", activeView === id ? "bg-cyan-300/10 text-cyan-100" : "text-slate-400 hover:bg-white/[0.05]")}><Icon className="h-4 w-4" />{label}</button>)}</nav><div className="mt-8 rounded-2xl border border-cyan-300/10 bg-cyan-300/[0.04] p-3 text-[11px] leading-5 text-slate-500">Local-first telemetry<br />ส่งข้อมูลจำเป็นไปยัง AI เท่านั้น</div></DialogContent></Dialog>;
}

function FilterBar({ filters, setFilters, stats, onClear, appChips, onOpenCommand }) {
  const activeFilterCount = [filters.type !== "ALL", filters.category !== "ALL", filters.hours !== 48, Boolean(filters.app), Boolean(filters.search)].filter(Boolean).length;
  return (
    <Card className="surface-panel p-3 sm:p-4">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center">
        <div className="flex rounded-xl border border-slate-400/10 bg-slate-950/60 p-1">
          {[['ALL', 'ทั้งหมด', stats?.total_events], ['CRASH', 'Crash', stats?.total_crashes], ['HANG', 'Hang', stats?.total_hangs]].map(([id, label, count]) => <button key={id} onClick={() => setFilters((current) => ({ ...current, type: id }))} className={cn("flex min-h-9 flex-1 items-center justify-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold transition", filters.type === id ? "bg-cyan-300/10 text-cyan-100 shadow-[inset_0_0_0_1px_rgba(103,232,249,.13)]" : "text-slate-400 hover:text-slate-100")}><span>{label}</span><span className="rounded-md bg-white/[0.07] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">{count ?? 0}</span></button>)}
        </div>
          <button onClick={onOpenCommand} className="group flex min-h-10 flex-1 items-center gap-2 rounded-xl border border-white/[0.08] bg-slate-950/40 px-3 text-left transition hover:border-cyan-300/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300/20">
          <Search className="h-4 w-4 shrink-0 text-slate-500 transition group-hover:text-cyan-200" /><span className={cn("min-w-0 flex-1 truncate text-sm", filters.search ? "text-slate-200" : "text-slate-500")}>{filters.search || "ค้นหา app, module หรือ exception code"}</span><kbd className="hidden rounded-md border border-white/10 px-1.5 py-0.5 font-mono text-[10px] text-slate-500 sm:inline">⌘ K</kbd>
          </button>
        <Button variant="ghost" size="sm" onClick={onClear} className="shrink-0"><X className="h-3.5 w-3.5" />ล้างตัวกรอง{activeFilterCount > 0 && <span className="rounded-full bg-cyan-300/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-200">{activeFilterCount}</span>}</Button>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-white/[0.06] pt-3">
        <span className="mr-1 inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500"><Filter className="h-3 w-3" /> Filters</span>
        <select value={filters.category} onChange={(event) => setFilters((current) => ({ ...current, category: event.target.value }))} className="filter-select"><option value="ALL">ทุกหมวดหมู่</option>{categories.slice(1).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select>
        <select value={filters.hours} onChange={(event) => setFilters((current) => ({ ...current, hours: Number(event.target.value) }))} className="filter-select"><option value="24">24 ชั่วโมง</option><option value="48">48 ชั่วโมง</option><option value="168">7 วัน</option><option value="720">30 วัน</option></select>
        <select value={filters.sortBy} onChange={(event) => setFilters((current) => ({ ...current, sortBy: event.target.value }))} className="filter-select"><option value="time_desc">ล่าสุดก่อน</option><option value="time_asc">เก่าสุดก่อน</option><option value="app_asc">ชื่อโปรแกรม A-Z</option></select>
        <div className="flex flex-1 flex-wrap gap-1.5 sm:justify-end">{(appChips || []).slice(0, 4).map((app) => <button key={app.name} onClick={() => setFilters((current) => ({ ...current, app: app.name }))} className={cn("rounded-full border px-2.5 py-1 text-[10px] font-semibold transition", filters.app === app.name ? "border-cyan-300/30 bg-cyan-300/10 text-cyan-100" : "border-slate-400/10 bg-white/[0.025] text-slate-400 hover:border-cyan-300/25 hover:text-slate-100")}>{app.name} · {app.count}</button>)}</div>
      </div>
    </Card>
  );
}

function groupByDay(events) {
  const groups = new Map();
  events.forEach((event) => {
    const key = String(event.time_created || "").slice(0, 10) || "unknown";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(event);
  });
  return Array.from(groups, ([key, items]) => ({ key, items }));
}

function dayLabel(key) {
  if (key === "unknown") return "ไม่ทราบวันที่";
  const date = new Date(`${key}T00:00:00`);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === today.toDateString()) return "วันนี้";
  if (date.toDateString() === yesterday.toDateString()) return "เมื่อวาน";
  return new Intl.DateTimeFormat("th-TH", { day: "numeric", month: "short", year: "numeric" }).format(date);
}

function IncidentFeed({ events, selected, onSelect, loading, error, onRefresh, onClear }) {
  const [density, setDensity] = useState("timeline");
  const groups = useMemo(() => groupByDay(events), [events]);
  return (
    <Card className="flex min-h-[520px] flex-col overflow-hidden">
      <div className="flex items-start justify-between gap-3 border-b border-slate-400/10 px-4 py-4 sm:px-5">
        <div><div className="eyebrow flex items-center gap-2"><Activity className="h-3.5 w-3.5" /> Incident feed</div><h2 className="mt-1 text-lg font-semibold text-white">เหตุการณ์ล่าสุด</h2></div>
        <div className="flex items-center gap-2"><Badge tone={events.length ? "cyan" : "neutral"}>{events.length} รายการ</Badge>{events.length > 10 && <div className="hidden rounded-lg border border-slate-400/10 bg-slate-950/60 p-0.5 sm:flex"><button aria-pressed={density === "timeline"} onClick={() => setDensity("timeline")} className={cn("rounded-md px-2 py-1 text-[10px] font-semibold", density === "timeline" ? "bg-cyan-300/10 text-cyan-100" : "text-slate-500")}>Timeline</button><button aria-pressed={density === "compact"} onClick={() => setDensity("compact")} className={cn("rounded-md px-2 py-1 text-[10px] font-semibold", density === "compact" ? "bg-cyan-300/10 text-cyan-100" : "text-slate-500")}>Compact</button></div>}</div>
      </div>
      <div className="flex-1 overflow-auto p-3 sm:p-4">
        {loading ? <div className="space-y-3"><Skeleton className="h-[102px]" /><Skeleton className="h-[102px]" /><Skeleton className="h-[102px]" /></div> : error ? <EmptyState icon={TriangleAlert} title="สแกนไม่สำเร็จ" description={error} tone="red" actionLabel="สแกนใหม่" onAction={onRefresh} /> : !events.length ? <EmptyState icon={Search} title="ไม่พบเหตุการณ์" description="ลองเพิ่มช่วงเวลาหรือล้างตัวกรองเพื่อค้นหาใหม่" actionLabel="ล้างตัวกรอง" onAction={onClear} /> : <div className="space-y-5">{groups.map(({ key, items }) => <section key={key}><div className="mb-2 flex items-center gap-2 px-1 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500"><span className="h-px w-4 bg-slate-500/40" />{dayLabel(key)}<span className="font-mono text-slate-600">{items.length}</span></div><div className={cn("relative space-y-2", density === "timeline" && "before:absolute before:bottom-3 before:left-[19px] before:top-3 before:w-px before:bg-slate-400/10")}>{items.map((event) => <IncidentRow key={`${event.record_id}-${event.time_created}`} event={event} compact={density === "compact"} selected={selected?.record_id === event.record_id && selected?.time_created === event.time_created} onClick={() => onSelect(event)} />)}</div></section>)}</div>}
      </div>
      <div className="border-t border-slate-400/10 px-4 py-3 text-[10px] leading-4 text-slate-500 sm:px-5">เลือก incident เพื่อเปิด investigation workspace · ข้อมูลอ่านจาก Windows Application Event Log{events.some(isSimulatedEvent) ? " + Demo Lab fallback" : ""}</div>
    </Card>
  );
}

function IncidentRow({ event, selected, onClick, compact }) {
  const tone = toneForSeverity(event.severity);
  const rail = tone === "red" ? "bg-rose-300" : tone === "amber" ? "bg-amber-300" : "bg-cyan-300";
  const label = event.severity || "MEDIUM";
  return <button onClick={onClick} aria-current={selected ? "true" : undefined} title={event.exception_meaning || undefined} className={cn("group relative z-10 flex min-h-14 w-full gap-3 overflow-hidden rounded-2xl border p-3 text-left transition duration-200", selected ? "border-cyan-300/45 bg-[#0F1C2E] shadow-[0_12px_32px_rgba(34,211,238,.10)]" : "border-transparent bg-white/[0.025] hover:border-slate-300/20 hover:bg-white/[0.055]")}>
    <span className={cn("absolute inset-y-0 left-0 w-0.5", rail)} /><span className={cn("mt-2 h-2.5 w-2.5 shrink-0 rounded-full ring-4 ring-[#0A1322]", rail)} />
    <span className="min-w-0 flex-1"><span className="flex flex-wrap items-center gap-2"><strong className="truncate text-sm text-slate-100">{event.app_name || "Unknown application"}</strong><Badge tone={tone}>{event.event_type}</Badge>{isSimulatedEvent(event) && <Badge tone="violet">SIMULATED</Badge>}<span className="text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500">{label}</span></span><span className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-slate-400"><code className="rounded-md bg-black/25 px-1.5 py-0.5 font-mono text-cyan-100/85">{event.event_type === "HANG" ? "EVENT 1002" : event.exception_code || "N/A"}</code><span>{event.module_name || "Unknown module"}</span></span>{!compact && <span className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-slate-500"><span>{relativeTime(event.time_created)}</span><span>•</span><span>{event.category_label || event.category || "ทั่วไป"}</span></span>}</span><span className="flex shrink-0 flex-col items-end justify-between gap-2"><span className="text-[10px] text-slate-500">{relativeTime(event.time_created)}</span><ChevronRight className={cn("h-4 w-4 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-cyan-200", selected && "text-cyan-200")} /></span>
  </button>;
}

function EmptyState({ icon: Icon, title, description, tone = "neutral", actionLabel, onAction }) {
  return <div className="flex min-h-[300px] flex-col items-center justify-center px-5 text-center"><div className={cn("flex h-12 w-12 items-center justify-center rounded-2xl border", tone === "red" ? "border-rose-300/20 bg-rose-400/10 text-rose-200" : "border-slate-400/10 bg-white/[0.04] text-slate-400")}><Icon className="h-5 w-5" /></div><strong className="mt-4 text-sm text-slate-200">{title}</strong><p className="mt-2 max-w-xs text-xs leading-5 text-slate-400">{description}</p>{actionLabel && onAction && <Button variant="secondary" size="sm" className="mt-4" onClick={onAction}>{actionLabel}</Button>}</div>;
}

function InvestigationPanel({ event, analysis, activeTab, setActiveTab, onAnalyze, onCopy, analysisLoading, toast }) {
  const [spotlight, setSpotlight] = useState({ x: 82, y: 0 });
  if (!event) return <Card className="flex min-h-[520px] items-center justify-center p-6"><EmptyState icon={ListFilter} title="เลือก incident เพื่อเริ่ม investigation" description="เลือกเหตุการณ์ทางซ้ายเพื่อดู Offline Diagnostic, OS telemetry และวิเคราะห์ด้วย Gemini" /></Card>;
  const tone = toneForSeverity(event.severity);
  return <Card className="investigation-card min-h-[520px] overflow-hidden xl:sticky xl:top-5" style={{ "--spot-x": `${spotlight.x}%`, "--spot-y": `${spotlight.y}%` }} onPointerMove={(eventPointer) => { const rect = eventPointer.currentTarget.getBoundingClientRect(); setSpotlight({ x: ((eventPointer.clientX - rect.left) / rect.width) * 100, y: ((eventPointer.clientY - rect.top) / rect.height) * 100 }); }}>
    <div className="border-b border-slate-400/10 bg-gradient-to-br from-white/[0.055] to-transparent p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3"><div className="flex min-w-0 items-start gap-3"><div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-cyan-300/20 bg-cyan-300/10 font-mono text-sm font-bold text-cyan-100">{(event.app_name || "?").slice(0, 2).toUpperCase()}</div><div className="min-w-0"><p className="eyebrow">Selected incident</p><h2 className="mt-1 break-all text-xl font-semibold tracking-tight text-white sm:text-2xl">{event.app_name || "Unknown application"}</h2><p className="mt-1 flex flex-wrap items-center gap-1.5 text-xs text-slate-400"><span>{event.module_name || "Unknown module"}</span><span className="text-slate-600">·</span><span>{formatTime(event.time_created)}</span></p></div></div><Button variant="ghost" size="icon" onClick={() => onCopy(JSON.stringify(event, null, 2), "คัดลอก Event JSON แล้ว")} title="คัดลอก JSON"><Clipboard className="h-4 w-4" /></Button></div>
      <div className="mt-4 flex flex-wrap items-center gap-2"><Badge tone={event.event_type === "HANG" ? "amber" : "red"}>{event.event_type} · ID {event.event_id}</Badge><Badge tone={tone}>{event.severity || "MEDIUM"}</Badge><Badge tone="cyan">{event.category_label || event.category}</Badge>{isSimulatedEvent(event) && <Badge tone="violet">SIMULATED DEMO</Badge>}<span className="font-mono text-[10px] text-slate-500">{event.signature_hash?.slice(0, 12) || "no-signature"}</span></div>
    </div>
    <Tabs value={activeTab} onValueChange={setActiveTab} className="p-4 sm:p-5"><TabsList className="sticky top-0 z-10 grid w-full grid-cols-4 bg-[#0A1322]/95 backdrop-blur"><TabsTrigger value="overview">ภาพรวม</TabsTrigger><TabsTrigger value="ai">AI Diagnosis</TabsTrigger><TabsTrigger value="telemetry">Telemetry</TabsTrigger><TabsTrigger value="raw">Raw</TabsTrigger></TabsList>
      <TabsContent value="overview"><Overview event={event} analysis={analysis} onAnalyze={onAnalyze} setActiveTab={setActiveTab} /></TabsContent>
      <TabsContent value="ai"><AiDiagnosis event={event} analysis={analysis} loading={analysisLoading} onAnalyze={onAnalyze} onCopy={onCopy} /></TabsContent>
      <TabsContent value="telemetry"><Telemetry event={event} onCopy={onCopy} /></TabsContent>
      <TabsContent value="raw"><RawEvent event={event} onCopy={onCopy} /></TabsContent>
    </Tabs>
  </Card>;
}

function Overview({ event, analysis, onAnalyze, setActiveTab }) {
  const checks = event.offline_checks || [];
  const [checked, setChecked] = useState(() => checks.map(() => false));
  useEffect(() => setChecked(checks.map(() => false)), [event.record_id, event.time_created]);
  const completed = checked.filter(Boolean).length;
  return <div className="space-y-3">
    <section className="glow-line rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.045] p-4"><div className="flex items-center justify-between gap-3"><div className="eyebrow flex items-center gap-2"><Gauge className="h-3.5 w-3.5" /> Offline diagnostic</div><Badge tone="green">LOCAL</Badge></div><p className="mt-3 text-sm leading-6 text-slate-100">{event.exception_meaning || "ยังไม่มีคำอธิบายเฉพาะสำหรับ exception นี้"}</p><p className="mt-2 flex items-center gap-1.5 text-[11px] text-slate-400"><Info className="h-3.5 w-3.5 text-cyan-200" /> เป็นข้อสังเกตเบื้องต้น ไม่ใช่ root cause ที่ยืนยันแล้ว</p></section>
    <section className="rounded-2xl border border-slate-400/10 bg-white/[0.025] p-4"><div className="flex items-start justify-between gap-3"><div><p className="eyebrow flex items-center gap-2 text-slate-400"><ListChecks className="h-3.5 w-3.5" /> Action checklist</p><p className="mt-1 text-xs text-slate-400">ขั้นตอนที่ปลอดภัยและไม่รันคำสั่งให้อัตโนมัติ</p></div><span className="font-mono text-xs text-slate-300">{completed}/{checks.length}</span></div><div className="mt-3 h-1 overflow-hidden rounded-full bg-white/[0.06]"><div className="h-full rounded-full bg-cyan-300 transition-all duration-200" style={{ width: checks.length ? `${(completed / checks.length) * 100}%` : "0%" }} /></div><div className="mt-3 space-y-1">{checks.length ? checks.map((check, index) => <label key={`${check}-${index}`} className="flex min-h-11 cursor-pointer items-start gap-3 rounded-xl border border-transparent p-2 transition hover:border-slate-300/15 hover:bg-white/[0.04]"><input type="checkbox" checked={Boolean(checked[index])} onChange={() => setChecked((current) => current.map((value, itemIndex) => itemIndex === index ? !value : value))} className="mt-0.5 h-4 w-4 accent-cyan-300" /><span className={cn("text-xs leading-5", checked[index] ? "text-slate-500 line-through" : "text-slate-300")}>{check}</span></label>) : <p className="text-xs text-slate-400">ไม่มี checklist สำหรับเหตุการณ์นี้</p>}</div></section>
    {analysis ? <section className="rounded-2xl border border-violet-300/15 bg-violet-400/[0.045] p-4"><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-violet-200"><Sparkles className="h-3.5 w-3.5" /> {sourceLabel(analysis.source)}</div><Badge tone={analysis.source === "offline" ? "amber" : analysis.source === "cache" ? "green" : "violet"}>{analysis.source}</Badge></div><h3 className="mt-3 text-sm font-semibold text-white">{analysis.diagnosis.simple_summary}</h3><p className="mt-2 line-clamp-3 text-xs leading-5 text-slate-400">{analysis.diagnosis.technical_explanation}</p><div className="mt-4 flex flex-wrap gap-2"><Button size="sm" onClick={() => setActiveTab("ai")}>ดู diagnosis เต็ม <ChevronRight className="h-3.5 w-3.5" /></Button><Button size="sm" variant="ghost" onClick={() => onAnalyze(true)}>วิเคราะห์ใหม่</Button></div></section> : <section className="rounded-2xl border border-dashed border-white/10 bg-white/[0.02] p-4"><div className="flex items-start gap-3"><div className="rounded-xl bg-violet-400/10 p-2.5 text-violet-200"><BrainCircuit className="h-4 w-4" /></div><div className="flex-1"><p className="text-xs font-semibold text-slate-200">AI-assisted diagnosis</p><p className="mt-1 text-xs leading-5 text-slate-500">สร้าง possible causes และ resolution playbook ด้วย Gemini หรือ Offline mode</p></div><Button size="sm" onClick={() => onAnalyze(false)}><Sparkles className="h-3.5 w-3.5" /> วิเคราะห์</Button></div></section>}
  </div>;
}

function likelihoodPercent(value) {
  return value === "HIGH" ? 88 : value === "MEDIUM" ? 58 : 30;
}

function AiDiagnosis({ event, analysis, loading, onAnalyze, onCopy }) {
  const [copiedCommand, setCopiedCommand] = useState("");
  if (loading) return <div className="space-y-4"><Skeleton className="h-28" /><div className="grid gap-3 sm:grid-cols-2"><Skeleton className="h-28" /><Skeleton className="h-28" /></div><Skeleton className="h-40" /></div>;
  if (!analysis) return <EmptyState icon={BrainCircuit} title="ยังไม่ได้วิเคราะห์" description="ระบบจะลองใช้ cache, Gemini และ Offline fallback ตามลำดับ" actionLabel="เริ่มวิเคราะห์" onAction={() => onAnalyze(false)} />;
  const diagnosis = analysis.diagnosis || {};
  return <div className="space-y-5"><div className="rounded-2xl border border-violet-300/20 bg-gradient-to-br from-violet-400/[0.14] to-cyan-300/[0.045] p-4"><div className="flex flex-wrap items-center justify-between gap-2"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-violet-100"><Sparkles className="h-3.5 w-3.5" /> {sourceLabel(analysis.source)}<Badge tone={analysis.source === "offline" ? "amber" : analysis.source === "cache" ? "green" : "violet"}>{analysis.source === "cache" ? "CACHE HIT" : analysis.source === "offline" ? "OFFLINE" : "GEMINI"}</Badge></div><div className="flex gap-2">{analysis.model && <Badge tone="neutral">{analysis.model}</Badge>}<Button size="sm" variant="ghost" onClick={() => onAnalyze(true)}><RefreshCw className="h-3.5 w-3.5" /> Retry</Button></div></div><h3 className="mt-4 text-base font-semibold leading-6 text-white">{diagnosis.simple_summary}</h3><p className="mt-2 text-xs leading-5 text-slate-300">{diagnosis.technical_explanation}</p>{analysis.warning && <div className="mt-3 flex gap-2 rounded-xl border border-amber-300/20 bg-amber-400/[0.08] p-3 text-xs leading-5 text-amber-100"><CircleAlert className="mt-0.5 h-4 w-4 shrink-0" />{analysis.warning}</div>}</div><section><SectionTitle icon={TriangleAlert} label="Probable causes" /><div className="mt-3 space-y-2">{(diagnosis.probable_causes || []).map((cause, index) => <div key={`${cause.cause}-${index}`} className="rounded-xl border border-slate-400/10 bg-white/[0.025] p-3"><div className="flex items-center justify-between gap-3"><strong className="text-xs text-slate-200">{cause.cause}</strong><Badge tone={cause.likelihood === "HIGH" ? "red" : cause.likelihood === "MEDIUM" ? "amber" : "neutral"}>{cause.likelihood}</Badge></div><div className="mt-2 flex items-center gap-2"><div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/[0.07]"><div className={cn("h-full rounded-full", cause.likelihood === "HIGH" ? "bg-rose-300" : cause.likelihood === "MEDIUM" ? "bg-amber-300" : "bg-slate-400")} style={{ width: `${likelihoodPercent(cause.likelihood)}%` }} /></div><span className="w-8 text-right font-mono text-[10px] text-slate-500">{likelihoodPercent(cause.likelihood)}%</span></div><p className="mt-2 text-xs leading-5 text-slate-400">{cause.reasoning}</p></div>)}</div></section><section><SectionTitle icon={Check} label="Resolution playbook" /><div className="mt-3 space-y-2">{(diagnosis.actionable_resolutions || []).map((resolution, index) => <div key={`${resolution.title}-${index}`} className="rounded-xl border border-slate-400/10 bg-white/[0.025] p-3"><div className="flex flex-wrap items-center gap-2"><Badge tone="cyan">{resolution.tier}</Badge><strong className="text-xs text-slate-200">{resolution.title}</strong></div><ul className="mt-2 space-y-1 text-xs leading-5 text-slate-400">{(resolution.steps || []).map((step, stepIndex) => <li key={`${step}-${stepIndex}`} className="flex gap-2"><span className="text-cyan-200">•</span>{step}</li>)}</ul>{resolution.command && <div className="mt-3 flex items-center gap-2 rounded-lg border border-slate-400/10 bg-black/20 p-2"><code className="min-w-0 flex-1 overflow-auto whitespace-nowrap font-mono text-[10px] text-cyan-100">{resolution.command}</code><Button size="icon" variant="ghost" onClick={async () => { await onCopy(resolution.command, "คัดลอกคำสั่งแล้ว — ระบบยังไม่ได้รันคำสั่งนี้"); setCopiedCommand(resolution.command); window.setTimeout(() => setCopiedCommand((value) => value === resolution.command ? "" : value), 1800); }} title="คัดลอกคำสั่ง">{copiedCommand === resolution.command ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Copy className="h-3.5 w-3.5" />}</Button></div>}</div>)}</div></section><section><SectionTitle icon={Search} label="Reference searches" /><div className="mt-3 flex flex-wrap gap-2">{(diagnosis.search_queries || []).map((query) => <a key={query} target="_blank" rel="noopener noreferrer" href={`https://www.google.com/search?q=${encodeURIComponent(query)}`} className="rounded-xl border border-slate-400/10 bg-white/[0.025] px-3 py-2 text-xs text-cyan-100 transition hover:border-cyan-300/25 hover:bg-cyan-300/[0.06]">ค้นหา: {query}</a>)}</div></section></div>;
}

function SectionTitle({ icon: Icon, label }) { return <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.13em] text-slate-400"><Icon className="h-3.5 w-3.5 text-cyan-200/80" /> {label}</div>; }

function Telemetry({ event, onCopy }) {
  const values = [["Exception code", event.exception_code, Code2], ["Symbol", event.exception_symbol, Terminal], ["Faulting module", event.module_name, FileJson], ["Fault offset", event.fault_offset, CrosshairIcon], ["Process ID", event.process_id, Activity], ["Application version", event.app_version, Settings2], ["Category", event.category, ListFilter], ["Signature hash", event.signature_hash, Database], ["Application path", event.app_path, HardDrive], ["Module path", event.module_path, HardDrive]];
  return <div className="grid gap-2 sm:grid-cols-2">{values.map(([label, value, Icon]) => <div key={label} className={cn("rounded-xl border border-slate-400/10 bg-white/[0.025] p-3", label.includes("path") && "sm:col-span-2")}><div className="flex items-center justify-between gap-3"><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.10em] text-slate-400"><Icon className="h-3 w-3" />{label}</div>{value && <button aria-label={`คัดลอก ${label}`} className="text-slate-500 transition hover:text-cyan-200" onClick={() => onCopy(String(value), `คัดลอก ${label} แล้ว`)}><Copy className="h-3 w-3" /></button>}</div><p className={cn("mt-2 break-all text-right text-xs text-slate-300", label === "Exception code" || label === "Signature hash" ? "font-mono text-cyan-100" : "")}>{value || "N/A"}</p></div>)}</div>;
}

function CrosshairIcon(props) { return <TargetIcon {...props} />; }
function TargetIcon({ className }) { return <span className={cn("inline-flex h-3.5 w-3.5 items-center justify-center rounded-full border border-current", className)} />; }

function RawEvent({ event, onCopy }) {
  const [wrap, setWrap] = useState(false);
  return <div className="overflow-hidden rounded-2xl border border-slate-400/10 bg-[#07101a]"><div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-400/10 px-3 py-2"><span className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-400"><FileJson className="h-3.5 w-3.5" /> Normalized payload</span><div className="flex items-center gap-1"><button aria-pressed={wrap} onClick={() => setWrap((value) => !value)} className="rounded-lg px-2 py-1 text-[10px] text-slate-500 hover:bg-white/[0.06] hover:text-slate-200">{wrap ? "No wrap" : "Wrap lines"}</button><Button variant="ghost" size="sm" onClick={() => onCopy(JSON.stringify(event, null, 2), "คัดลอก Raw JSON แล้ว")}><Clipboard className="h-3.5 w-3.5" />Copy</Button></div></div><pre className={cn("max-h-[510px] overflow-auto p-4 font-mono text-[10px] leading-5 text-cyan-100/80", wrap ? "whitespace-pre-wrap break-words" : "whitespace-pre")}>{JSON.stringify(event, null, 2)}</pre></div>;
}

function DemoLab({ onSimulate, loading }) {
  const [open, setOpen] = useState(false);
  const [pending, setPending] = useState(null);
  return <Card className="overflow-hidden"><div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-5"><div className="flex items-center gap-3"><div className="rounded-xl border border-amber-300/15 bg-amber-400/10 p-2 text-amber-200"><Zap className="h-4 w-4" /></div><div><h2 className="text-sm font-semibold text-slate-200">Demo Lab</h2><p className="mt-0.5 text-[11px] text-slate-600">จำลอง crash/hang ใน process แยกเพื่อทดสอบระบบ</p></div></div><Button variant="ghost" size="sm" onClick={() => setOpen((value) => !value)}><MoreHorizontal className="h-4 w-4" />{open ? "ซ่อน" : "เปิด"}</Button></div>{open && <div className="border-t border-white/[0.08] bg-white/[0.02] px-4 py-4 sm:px-5"><div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">{simulations.map(([type, label, description, variant]) => <button key={type} disabled={loading} onClick={() => setPending([type, label])} className={cn("group rounded-xl border p-3 text-left transition hover:-translate-y-0.5", variant === "danger" ? "border-rose-300/15 bg-rose-400/[0.04] hover:border-rose-300/35" : "border-amber-300/15 bg-amber-400/[0.04] hover:border-amber-300/35")}><span className={cn("flex items-center gap-2 text-xs font-semibold", variant === "danger" ? "text-rose-100" : "text-amber-100")}><Play className="h-3.5 w-3.5 transition group-hover:translate-x-0.5" />{label}</span><span className="mt-2 block text-[10px] leading-4 text-slate-600">{description}</span></button>)}</div><p className="mt-3 flex items-center gap-2 text-[10px] leading-4 text-slate-600"><AlertTriangle className="h-3 w-3 text-amber-200/70" />การจำลองอาจใช้เวลาหลายวินาที และ Windows อาจใช้เวลาสักครู่ก่อนเขียน Event Log</p></div>}
    <AlertDialog open={Boolean(pending)} onOpenChange={(value) => !value && setPending(null)}><AlertDialogContent><AlertDialogTitle className="text-lg font-semibold text-white">ยืนยันการจำลองเหตุการณ์</AlertDialogTitle><AlertDialogDescription className="mt-2 text-sm leading-6 text-slate-400">ระบบจะเปิด process แยกเพื่อจำลอง <strong className="text-amber-100">{pending?.[1]}</strong> และอาจสร้างรายการใหม่ใน Windows Event Log คุณต้องการดำเนินการต่อหรือไม่</AlertDialogDescription><div className="mt-5 flex justify-end gap-2"><AlertDialogCancel asChild><Button variant="ghost">ยกเลิก</Button></AlertDialogCancel><AlertDialogAction asChild><Button onClick={async () => { const type = pending[0]; setPending(null); await onSimulate(type); }}><Play className="h-3.5 w-3.5" />ยืนยันจำลอง</Button></AlertDialogAction></div></AlertDialogContent></AlertDialog>
  </Card>;
}

function Toast({ message, onClose }) {
  if (!message) return null;
  return <div role="status" aria-live="polite" className="fixed bottom-5 right-5 z-50 flex max-w-sm items-start gap-3 overflow-hidden rounded-2xl border border-cyan-300/20 bg-[#0d1a2d]/95 px-4 py-3 text-xs text-cyan-50 shadow-2xl backdrop-blur-xl"><Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /><span className="flex-1 leading-5">{message}</span><button onClick={onClose} className="text-slate-500 hover:text-white" aria-label="ปิดข้อความ"><X className="h-3.5 w-3.5" /></button><span className="toast-progress pointer-events-none absolute inset-x-0 bottom-0 h-0.5 origin-left bg-cyan-300/80" /></div>;
}

function CommandMenu({ open, onOpenChange, onRefresh, onClearFilters, onNavigate, events, onSelectEvent }) {
  return <CommandDialog open={open} onOpenChange={onOpenChange}>
    <CommandInput placeholder="ค้นหา incident หรือ action..." autoFocus />
    <CommandList>
      <CommandEmpty>ไม่พบรายการ</CommandEmpty>
      <CommandGroup heading="Navigation">
        <CommandItem onSelect={() => { onOpenChange(false); onNavigate("dashboard", "system-pulse"); }}><LayoutDashboard className="h-4 w-4" />Mission control</CommandItem>
        <CommandItem onSelect={() => { onOpenChange(false); onNavigate("events", "incident-feed"); }}><Activity className="h-4 w-4" />Event stream</CommandItem>
        <CommandItem onSelect={() => { onOpenChange(false); onNavigate("diagnostics", "investigation-workspace"); }}><BrainCircuit className="h-4 w-4" />AI diagnostics</CommandItem>
      </CommandGroup>
      <CommandGroup heading="Actions">
        <CommandItem onSelect={() => { onOpenChange(false); onRefresh(); }}><RefreshCw className="h-4 w-4" />สแกน Event Log ใหม่</CommandItem>
        <CommandItem onSelect={() => { onOpenChange(false); onClearFilters(); }}><Filter className="h-4 w-4" />ล้างตัวกรองทั้งหมด</CommandItem>
        <CommandItem onSelect={() => { onOpenChange(false); onNavigate("demo", "demo-lab"); }}><Zap className="h-4 w-4" />เปิด Demo Lab</CommandItem>
      </CommandGroup>
      <CommandGroup heading="Recent incidents">
        {(events || []).slice(0, 8).map((event) => <CommandItem key={`${event.record_id}-${event.time_created}`} value={`${event.app_name} ${event.exception_code} ${event.module_name}`} onSelect={() => { onOpenChange(false); onSelectEvent(event); }}><Activity className="h-4 w-4 text-cyan-200" /><span className="min-w-0 flex-1 truncate">{event.app_name}</span><code className="text-[10px] text-slate-500">{event.exception_code || `EVENT ${event.event_id}`}</code></CommandItem>)}
      </CommandGroup>
    </CommandList>
  </CommandDialog>;
}

export default function DashboardApp() {
  const [system, setSystem] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [filters, setFilters] = useState({ type: "ALL", category: "ALL", hours: 48, app: "", sortBy: "time_desc", search: "" });
  const [selected, setSelected] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [activeView, setActiveView] = useState("dashboard");
  const [commandOpen, setCommandOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [error, setError] = useState("");
  const [analyses, setAnalyses] = useState(() => new Map());
  const [toast, setToast] = useState("");
  const requestController = useRef(null);

  const events = useMemo(() => {
    const query = filters.search.trim().toLowerCase();
    return (dashboard?.events || []).filter((event) => !query || [event.app_name, event.module_name, event.exception_code, event.category_label, event.category].filter(Boolean).join(" ").toLowerCase().includes(query));
  }, [dashboard, filters.search]);

  const notify = (message) => { setToast(message); window.setTimeout(() => setToast(""), 4200); };

  useEffect(() => {
    getSystemInfo().then(setSystem).catch(() => notify("เชื่อมต่อ Local Backend ไม่สำเร็จ"));
  }, []);

  useEffect(() => {
    const onKey = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const targets = ["system-pulse", "incident-feed", "investigation-workspace", "demo-lab"].map((id) => document.getElementById(id)).filter(Boolean);
    if (!targets.length) return undefined;
    const observer = new IntersectionObserver((entries) => {
      const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActiveView(visible.target.dataset.nav || "dashboard");
    }, { rootMargin: "-20% 0px -65% 0px", threshold: [0.1, 0.4, 0.8] });
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, [dashboard]);

  useEffect(() => {
    refresh();
    return () => requestController.current?.abort();
  }, [filters.type, filters.category, filters.hours, filters.app, filters.sortBy]);

  useEffect(() => {
    if (events.length && !events.some((event) => event.record_id === selected?.record_id && event.time_created === selected?.time_created)) setSelected(events[0]);
    if (!events.length) setSelected(null);
  }, [events, selected]);

  async function refresh() {
    requestController.current?.abort();
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true); setError("");
    try { setDashboard(await getDashboard(filters, controller.signal)); } catch (requestError) { if (requestError.name !== "AbortError") { setError(requestError.message); setDashboard(null); } } finally { if (requestController.current === controller) setLoading(false); }
  }

  async function runAnalysis(forceRefresh) {
    if (!selected) return;
    setAnalysisLoading(true); setActiveTab("ai");
    try { const result = await analyzeEvent(selected, forceRefresh); setAnalyses((previous) => new Map(previous).set(selected.signature_hash, result)); notify(`${sourceLabel(result.source)} พร้อมใช้งาน`); } catch (analysisError) { notify(analysisError.message); } finally { setAnalysisLoading(false); }
  }

  async function runSimulation(type) {
    notify(`กำลังจำลอง ${type}...`);
    try { await simulateEvent(type); notify("จำลองสำเร็จ กำลังสแกน Event Log ใหม่"); window.setTimeout(refresh, 1500); } catch (simulationError) { notify(simulationError.message); }
  }

  function clearFilters() { setFilters({ type: "ALL", category: "ALL", hours: 48, app: "", sortBy: "time_desc", search: "" }); }
  function navigate(id, target) { setActiveView(id); document.getElementById(target)?.scrollIntoView({ behavior: "smooth", block: "start" }); }
  function selectEvent(event) { setSelected(event); setActiveTab("overview"); document.getElementById("investigation-workspace")?.scrollIntoView({ behavior: "smooth", block: "start" }); }

  const stats = dashboard?.stats || {};
  const extractor = dashboard?.extractor || {};
  const analysis = selected ? analyses.get(selected.signature_hash) : null;
  const totalEvents = Number(stats.total_events || 0);
  const crashRatio = totalEvents ? Math.round((Number(stats.total_crashes || 0) / totalEvents) * 100) : 0;
  const hangRatio = totalEvents ? Math.round((Number(stats.total_hangs || 0) / totalEvents) * 100) : 0;
  const impactRatio = totalEvents ? Math.round(((Number(stats.total_critical || 0) + Number(stats.total_high || 0)) / totalEvents) * 100) : 0;
  const copy = (value, message) => copyToClipboard(value).then(() => notify(message)).catch(() => notify("Clipboard ใช้งานไม่ได้บน browser นี้"));

  return <div className="app-grid noise min-h-screen"><div className="mx-auto flex min-h-screen w-full max-w-[1800px]"><Sidebar system={system} activeView={activeView} onNavigate={navigate} /><div className="min-w-0 flex-1"><CommandBar system={system} extractor={extractor} loading={loading} error={error} onRefresh={refresh} onOpenCommand={() => setCommandOpen(true)} activeView={activeView} onOpenMobileNav={() => setMobileNavOpen(true)} scannedAt={dashboard?.scanned_at} /><main className="space-y-5 px-4 py-5 sm:px-6 lg:space-y-6 lg:px-8 lg:py-7"><section id="system-pulse" data-nav="dashboard" className="scroll-mt-6 flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs text-slate-400">{dashboard?.scanned_at ? `สแกนล่าสุด ${formatTime(dashboard.scanned_at)}` : "กำลังเชื่อมต่อ Event Log..."}</p><h2 className="mt-1 text-2xl font-semibold tracking-tight text-white">System pulse</h2></div><div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.12em] text-slate-500"><TimerReset className="h-3.5 w-3.5" />ย้อนหลัง {filters.hours} ชั่วโมง</div></section><section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><StatCard icon={Activity} label="Events in window" value={loading ? "—" : stats.total_events ?? 0} helper={`ย้อนหลัง ${filters.hours} ชั่วโมง`} tone="cyan" ratio={loading ? undefined : totalEvents ? 100 : 0} /><StatCard icon={TriangleAlert} label="Application crash" value={loading ? "—" : stats.total_crashes ?? 0} helper="Event ID 1000 / 1001" tone="red" ratio={loading ? undefined : crashRatio} /><StatCard icon={TimerReset} label="Application hang" value={loading ? "—" : stats.total_hangs ?? 0} helper="Event ID 1002" tone="amber" ratio={loading ? undefined : hangRatio} /><StatCard icon={ShieldCheck} label="High impact" value={loading ? "—" : (stats.total_critical || 0) + (stats.total_high || 0)} helper={`top app: ${stats.top_failing_app || "—"}`} tone="violet" ratio={loading ? undefined : impactRatio} /></section><FilterBar filters={filters} setFilters={setFilters} stats={stats} onClear={clearFilters} appChips={stats.top_apps} onOpenCommand={() => setCommandOpen(true)} /><section id="incident-feed" data-nav="events" className="scroll-mt-6 grid items-start gap-4 xl:grid-cols-[minmax(0,0.38fr)_minmax(0,0.62fr)]"><IncidentFeed events={events} selected={selected} onSelect={selectEvent} loading={loading} error={error} onRefresh={refresh} onClear={clearFilters} /><div id="investigation-workspace" data-nav="diagnostics" className="scroll-mt-6"><InvestigationPanel event={selected} analysis={analysis} activeTab={activeTab} setActiveTab={setActiveTab} onAnalyze={runAnalysis} onCopy={copy} analysisLoading={analysisLoading} /></div></section><section id="demo-lab" data-nav="demo" className="scroll-mt-6"><DemoLab onSimulate={runSimulation} loading={loading} /></section><footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-400/10 pt-4 text-[10px] leading-4 text-slate-500"><span className="flex items-center gap-1.5"><ServerCog className="h-3 w-3" /> {engineLabel(extractor.engine_used)} · {extractor.duration_ms ? `${Math.round(extractor.duration_ms)} ms` : "รอผล scan"}</span><span>ไม่ส่ง machine name, PID หรือ full path ไปยัง Gemini</span></footer></main></div></div><MobileNavigation open={mobileNavOpen} onOpenChange={setMobileNavOpen} activeView={activeView} onNavigate={navigate} /><CommandMenu open={commandOpen} onOpenChange={setCommandOpen} onRefresh={refresh} onClearFilters={clearFilters} onNavigate={navigate} events={events} onSelectEvent={selectEvent} /><Toast message={toast} onClose={() => setToast("")} /></div>;
}
