# WinEvent Analyzer

ระบบ Local Web App สำหรับตรวจจับ วิเคราะห์ และอธิบาย Windows Application Crash/Hang จาก `Windows Event Log` โดยผสาน OS telemetry, Offline Diagnosis, Gemini Structured Output และ SQLite Cache ไว้ในหน้าเดียว

> **Operating Systems Mini Project** · Windows Event Log · SEH/NTSTATUS · Message Loop · FastAPI · React

![status](https://img.shields.io/badge/status-local%20app-22c55e)
![platform](https://img.shields.io/badge/platform-Windows%2010%2F11-2563eb)
![tests](https://img.shields.io/badge/tests-pytest%20%2B%20Vitest-8b5cf6)

## ภาพรวม

เมื่อโปรแกรมบน Windows crash หรือไม่ตอบสนอง ระบบปฏิบัติการจะทิ้งหลักฐานไว้ใน Application Event Log แต่ข้อมูลดิบมักอ่านยาก โปรเจกต์นี้จึงทำหน้าที่เป็น investigation console ที่แปลงหลักฐานระดับ OS ให้เป็นข้อมูลที่ค้นหาและวิเคราะห์ต่อได้:

~~~text
Windows Event Log
        ↓
Native pywin32 / PowerShell fallback
        ↓
XML Parser + Error Mapping
        ↓
Offline Diagnosis ── Gemini Structured Output
        ↓                  ↓
        └──── SQLite Cache
                  ↓
        React SRE Mission Control
~~~

ระบบรองรับทั้งกรณีมีและไม่มี API key โดย Offline Diagnosis จะยังทำงานได้เมื่อ Gemini ใช้งานไม่ได้, timeout หรือ quota ไม่พร้อม

## ความสามารถหลัก

- อ่าน Event ID `1000`, `1001` และ `1002` จาก channel `Application`
- ใช้ `pywin32` เป็น native extractor และ fallback ไป `PowerShell Get-WinEvent` อัตโนมัติ
- รายงาน engine ที่อ่านข้อมูลสำเร็จจริง พร้อม duration และ fallback reason
- แปลง Event XML เป็น Pydantic `CrashEvent` ที่มี category, severity และ exception meaning
- วิเคราะห์แบบ Offline ได้โดยไม่ต้องส่งข้อมูลออกจากเครื่อง
- เชื่อม Gemini ผ่าน `google-genai` และบังคับ Structured Output ด้วย Pydantic schema
- Cache เฉพาะผล Gemini ที่ validate สำเร็จ โดยแยกตาม signature, model และ prompt version
- Dashboard React + Vite + Tailwind + shadcn-style primitives แบบ Thai-first
- Demo Lab จำลอง crash/hang ใน child process ที่ allowlist ไว้
- ทำงานบน `127.0.0.1` เท่านั้น และไม่ expose source frontend ใน production

## จุดเชื่อมโยงกับวิชา OS

| แนวคิด OS | สิ่งที่แสดงในโปรเจกต์ |
| --- | --- |
| Windows Event Logging | อ่าน Application channel และแยก Event ID 1000/1001/1002 |
| Structured Exception Handling | จำลอง crash เช่น access violation, breakpoint และ runtime abort |
| NTSTATUS / Exception Code | แปลง `0xc0000005`, `0xc0000409`, `0x80000003` เป็นความหมายและ severity |
| Process isolation | Demo Lab สั่งงานผ่าน child process ไม่ใช่ process ของ dashboard |
| Windows Message Loop | จำลอง GUI hang และแสดง Application Hang telemetry |
| Native API / fallback | เปรียบเทียบ pywin32 C API กับ PowerShell Event Log API |
| Caching and normalization | ใช้ signature hash และ SQLite ลดการวิเคราะห์ซ้ำ |

## Requirements

- Windows 10/11
- Python 3.11–3.13
- Node.js 20+ และ npm
- PowerShell (มีมากับ Windows)
- สิทธิ์อ่าน Application Event Log
- `GEMINI_API_KEY` เป็น optional

## Quick Start

เปิด PowerShell ในโฟลเดอร์โปรเจกต์:

~~~powershell
cd C:\Users\User\Downloads\OS\WinEvent-AI-Analyzer-OS-project
~~~

### 1. ติดตั้ง backend

~~~powershell
python -m pip install -r requirements.txt
~~~

หากต้องการแยก environment:

~~~powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
~~~

### 2. Build frontend ครั้งแรก

~~~powershell
cd frontend
npm install
npm run build
cd ..
~~~

### 3. เปิดระบบ

~~~powershell
.\run.bat
~~~

ระบบจะรอจน FastAPI พร้อม แล้วเปิด [http://127.0.0.1:8000](http://127.0.0.1:8000) ให้โดยอัตโนมัติ

> หลังแก้ React frontend ต้องรัน `npm run build` ใหม่ก่อนใช้ `run.bat` ระบบจะไม่ติดตั้ง dependency แบบเงียบ ๆ

## Gemini และ Offline Mode

คัดลอกตัวอย่าง configuration:

~~~powershell
Copy-Item .env.example .env
~~~

แล้วกำหนดค่าใน `.env`:

~~~text
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.1-flash-lite
AI_TIMEOUT_SECONDS=20
CACHE_DB_PATH=data/winevent_analyzer.db
PROMPT_VERSION=v1
~~~

ข้อควรระวัง:

- ห้าม commit `.env` หรือ API key
- key อยู่ฝั่ง backend และไม่ถูกส่งไป frontend
- backend จะส่งเฉพาะ telemetry ที่จำเป็น เช่น app, module, exception code, category และ severity
- ไม่ส่ง machine name, PID, report ID หรือ full path ไป Gemini
- หากไม่มี key, Gemini timeout, 429, 5xx หรือ schema ไม่ถูกต้อง ระบบจะใช้ Offline Diagnosis ต่อ

## วิธีใช้ Dashboard

1. กด `Scan Now` เพื่ออ่าน Event Log ในช่วงเวลาที่เลือก
2. เลือก incident จาก Incident Feed
3. ดู `Overview` เพื่ออ่าน offline diagnostic และ checklist
4. เปิด `AI Diagnosis` เพื่อวิเคราะห์ด้วย Gemini หรือดูผลจาก cache
5. ใช้ `Telemetry` และ `Raw` เพื่อตรวจสอบข้อมูลระดับ OS
6. กด `Demo Lab` หากต้องการสร้างเหตุการณ์ทดสอบ

### Demo Lab

ทุก simulation ทำงานใน process แยกและต้องยืนยันก่อนเริ่ม:

| Type | Event | Code / ลักษณะ |
| --- | ---: | --- |
| `.NET FailFast` | 1000 | `0x80131623` · runtime fail-fast |
| `C-Runtime abort` | 1000 | `0xc0000409` · process abort |
| `Access Violation` | 1000 | `0xc0000005` · invalid memory access |
| `DebugBreak` | 1000 | `0x80000003` · breakpoint/assertion |
| `GUI Hang` | 1002 | message loop ไม่ตอบสนอง |

Windows อาจใช้เวลาสักครู่ก่อนบันทึก Event Log และ GUI Hang แบบ short-lived อาจไม่สร้าง Event ID 1002 จริง ระบบจึงแสดง local fallback ที่ติดป้าย `SIMULATED` อย่างชัดเจนในกรณีนี้

## API ที่สำคัญ

| Method | Endpoint | หน้าที่ |
| --- | --- | --- |
| `GET` | `/api/system-info` | OS, Python, native availability, AI และ cache status |
| `GET` | `/api/dashboard` | อ่าน Event Log หนึ่งครั้งแล้วคืน events, stats, extractor และ filters |
| `GET` | `/api/events` | compatibility endpoint สำหรับรายการ events |
| `GET` | `/api/stats` | compatibility endpoint สำหรับ KPI |
| `POST` | `/api/analyze` | Gemini, cache หรือ offline diagnosis |
| `POST` | `/api/simulate` | เรียก simulation type ที่อยู่ใน allowlist เท่านั้น |

ตัวอย่าง:

~~~powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/system-info"
Invoke-RestMethod "http://127.0.0.1:8000/api/dashboard?hours=48&limit=100"
~~~

## Development Workflow

รัน backend:

~~~powershell
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
~~~

รัน Vite dev server ในอีก terminal:

~~~powershell
cd frontend
npm run dev
~~~

เปิด [http://127.0.0.1:5173](http://127.0.0.1:5173) โดย Vite จะ proxy `/api` ไปยัง FastAPI port 8000

## Tests และ Verification

Backend:

~~~powershell
pytest -q --basetemp .pytest-tmp
~~~

Frontend:

~~~powershell
cd frontend
npm ci
npm run test -- --run
npm run build
cd ..
~~~

Smoke test แบบ CLI:

~~~powershell
python scripts/test_extractor.py --hours 48 --limit 5
python scripts/test_extractor.py --type CRASH --hours 48
python scripts/test_extractor.py --type HANG --hours 720
python scripts/crash_simulator.py --type access_violation
~~~

ชุดทดสอบครอบคลุม parser, native/fallback extractor, cache, offline diagnosis, API validation และ simulation allowlist โดย test suite ปกติไม่เรียก Gemini จริง

## โครงสร้างโปรเจกต์

~~~text
backend/
├─ app.py                    FastAPI routes และ dashboard snapshot
├─ models.py                 Pydantic contracts
├─ config.py                 environment-backed settings
├─ database.py               SQLite WAL cache
├─ extractor/
│  ├─ event_reader.py        pywin32 + PowerShell extractor
│  ├─ parser.py              Event XML parser
│  └─ error_codes.py         offline exception dictionary
└─ ai_engine/
   ├─ gemini_analyzer.py     Gemini adapter, retry และ fallback
   ├─ offline.py             deterministic diagnosis
   └─ prompts.py             privacy-safe telemetry projection

frontend/
├─ src/components/dashboard.jsx  main React workspace
├─ src/components/ui.jsx         UI primitives
├─ src/index.css                 design tokens และ responsive styles
├─ src/api.js                    same-origin API client
└─ vite.config.js                production build และ dev proxy

scripts/crash_simulator.py       isolated Demo Lab process
tests/                            backend pytest suite
docs/CODE_EXPLANATION.md          technical architecture guide
run.bat                           Windows launcher
~~~

## Privacy, Safety และขอบเขต

- เป็น local-only app ไม่มี account และไม่มี cloud deployment
- bind server ที่ `127.0.0.1` เท่านั้น
- simulator ไม่รับ arbitrary command จาก API
- ระบบไม่สั่งคำสั่งแก้ไข OS ให้อัตโนมัติ คำสั่งใน diagnosis เป็นคำแนะนำให้ copy เท่านั้น
- ไม่ commit `.env`, API key, SQLite database, logs, `node_modules` หรือ `dist`
- ผลจาก Gemini เป็น Possible Causes ไม่ใช่การยืนยัน root cause

## Troubleshooting

### หน้าเว็บขึ้น `Frontend build ยังไม่พร้อม`

~~~powershell
cd frontend
npm install
npm run build
cd ..
.\run.bat
~~~

### ไม่มี event แสดง

- เพิ่มช่วงเวลาเป็น 30 วัน
- ตรวจว่า channel เป็น `Application`
- รัน `python scripts/test_extractor.py --hours 720`
- ใช้ Demo Lab เพื่อสร้าง event ทดสอบ

### Gemini ใช้งานไม่ได้

ระบบยังแสดง Offline Diagnosis ได้ตามปกติ ตรวจสอบ `GEMINI_API_KEY`, `GEMINI_MODEL`, network และ quota ใน `.env` แล้ว restart server

### Native extractor ใช้งานไม่ได้

ดูแถบสถานะ `PowerShell fallback` และ `fallback_reason` บน dashboard ระบบจะพยายามอ่านด้วย `Get-WinEvent` ต่อให้อัตโนมัติ

## เอกสารเพิ่มเติม

- [คู่มือสถาปัตยกรรมและการทำงานของโค้ด](docs/CODE_EXPLANATION.md)
- [แผนการพัฒนาและขอบเขตโปรเจกต์](plan.md)
