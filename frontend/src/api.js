export async function getSystemInfo() {
  const response = await fetch("/api/system-info");
  if (!response.ok) throw new Error("อ่านข้อมูลระบบไม่สำเร็จ");
  return response.json();
}

export async function getDashboard(filters, signal) {
  const params = new URLSearchParams({
    hours: String(filters.hours),
    limit: "500",
    type: filters.type,
    sort_by: filters.sortBy,
  });
  if (filters.category !== "ALL") params.set("category", filters.category);
  if (filters.app) params.set("app", filters.app);
  const response = await fetch(`/api/dashboard?${params.toString()}`, { signal });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "โหลด Event Log ไม่สำเร็จ");
  return data;
}

export async function analyzeEvent(event, forceRefresh = false) {
  const response = await fetch("/api/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event, force_refresh: forceRefresh }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "วิเคราะห์เหตุการณ์ไม่สำเร็จ");
  return data;
}

export async function simulateEvent(simulationType) {
  const response = await fetch("/api/simulate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ simulation_type: simulationType }),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "จำลองเหตุการณ์ไม่สำเร็จ");
  return data;
}
