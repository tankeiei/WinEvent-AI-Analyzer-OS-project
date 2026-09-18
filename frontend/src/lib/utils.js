import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatTime(value) {
  if (!value) return "ไม่ทราบเวลา";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 19).replace("T", " ");
  return date.toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
}

export function relativeTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "ไม่ทราบเวลา";
  const seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
  if (seconds < 60) return `${seconds} วินาทีที่แล้ว`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} นาทีที่แล้ว`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} ชั่วโมงที่แล้ว`;
  return `${Math.round(seconds / 86400)} วันที่แล้ว`;
}

export function sourceLabel(source) {
  if (source === "cache") return "CACHE HIT";
  if (source === "gemini") return "GEMINI";
  return "OFFLINE";
}

export function severityTone(value = "MEDIUM") {
  return String(value).toLowerCase().replaceAll("_", "-");
}

export async function copyToClipboard(value) {
  await navigator.clipboard.writeText(value);
}
