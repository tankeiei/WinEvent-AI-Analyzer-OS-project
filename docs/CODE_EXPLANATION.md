# WinEvent Analyzer — Technical Architecture Guide

เอกสารนี้อธิบายการทำงานภายในของ WinEvent Analyzer สำหรับใช้ประกอบการอ่าน source code, demo และการนำเสนอ Mini Project วิชา Operating Systems

## 1. Problem และ OS Context

Windows Application Event Log เก็บหลักฐานหลังเกิด crash หรือ application hang ไว้ใน channel `Application` โปรเจกต์สนใจเหตุการณ์หลัก 3 กลุ่ม:

| Event ID | Provider | ความหมาย |
| ---: | --- | --- |
| `1000` | Application Error | process จบลงจาก unhandled exception หรือ native/runtime failure |
| `1001` | Windows Error Reporting | WER telemetry และ report/bucket context ที่เกี่ยวข้องกับ crash |
| `1002` | Application Hang | หน้าต่างหรือ UI message loop ไม่ตอบสนอง |

ตัวอย่าง exception code ที่ใช้สาธิต:

- `0xc0000005` — `STATUS_ACCESS_VIOLATION`
- `0xc0000409` — C-Runtime / fail-fast boundary
- `0x80000003` — `STATUS_BREAKPOINT`
- `0x80131623` — `.NET FailFast`

หลักสำคัญของระบบคือ Event Log เป็นหลักฐานของ failure boundary ไม่ใช่ call stack เต็มหรือ root cause ที่ยืนยันแล้ว ดังนั้นทั้ง Offline Diagnosis และ Gemini ใช้ถ้อยคำ `Possible Causes` และ `Suggested Diagnosis`

## 2. End-to-End Pipeline

~~~text
Demo Lab / real application failure
              ↓
Windows Application Event Log
              ↓
pywin32 EvtQuery ── failure ──→ PowerShell Get-WinEvent
              ↓
Event XML parser + named/positional fields
              ↓
CrashEvent + exception/category/severity enrichment
              ↓
Offline Diagnosis ── optional ──→ Gemini Structured Output
              ↓                         ↓
              └──────── SQLite cache ───┘
                              ↓
                     React Mission Control
~~~

### 2.1 Extraction layer

`backend/extractor/event_reader.py` มี `read_event_log()` เป็น entry point หลักและคืน `EventReadResult` ที่ประกอบด้วย:

- `events` — รายการ `CrashEvent`
- `metadata.engine_used` — `pywin32`, `powershell` หรือ `unavailable`
- `metadata.native_available` — สถานะการ import native API
- `metadata.fallback_reason` — เหตุผลที่ native หรือ fallback ล้มเหลว
- `metadata.duration_ms` — เวลาที่ใช้ในการอ่าน log

Native path ใช้ signature ปัจจุบันของ pywin32:

~~~python
win32evtlog.EvtQuery("Application", flags, query_xpath)
win32evtlog.EvtRender(event_handle, win32evtlog.EvtRenderEventXml)
~~~

การตัดสินว่าใช้ engine ใดอิงจากผลการอ่านข้อมูลสำเร็จจริง ไม่ได้อิงเพียงการ import package สำเร็จ

### 2.2 Parser และ normalization

`backend/extractor/parser.py` ทำงานตามลำดับ:

1. ลบ default XML namespace เพื่อให้ query field ได้สม่ำเสมอ
2. อ่าน `System.EventID`, `EventRecordID` และ `TimeCreated`
3. เก็บ `EventData` ทั้ง named fields และ positional values
4. เลือก mapping ตาม Event ID
5. เติม diagnostic metadata จาก `error_codes.py`
6. สร้าง Pydantic `CrashEvent`

การใช้ named field ก่อน positional field ช่วยรองรับ XML ที่รูปแบบต่างกันระหว่าง Windows version และ provider ส่วน field ที่หายจะใช้ safe default แทนการทำให้ทั้ง scan ล้มเหลว

สำหรับ Event `1002` parser จะกำหนด `event_type=HANG`, `exception_code=N/A`, ดึง `HangType` และใช้ `UI Message Loop / Thread` เป็น module representation สำหรับการวิเคราะห์

### 2.3 Shared data contract

`backend/models.py` เป็น contract กลางระหว่าง extractor, API, AI และ frontend โดย `CrashEvent` เก็บข้อมูลสำคัญ เช่น:

| Field | ใช้ทำอะไร |
| --- | --- |
| `event_id`, `event_type` | แยก crash/hang และ provider event |
| `app_name`, `module_name` | ระบุ process และ failure boundary |
| `exception_code`, `exception_symbol` | เชื่อมกับ NTSTATUS/diagnostic dictionary |
| `category`, `severity` | ใช้ filter, KPI และการจัดลำดับความสำคัญ |
| `exception_meaning`, `offline_checks` | สรุปออฟไลน์และ checklist |
| `record_id + time_created` | identity ของ incident ใน UI |
| `signature_hash` | identity ของ failure pattern สำหรับ AI cache |

`signature_hash` เป็น Pydantic `computed_field` ที่ normalize event type, app, module และ exception code ก่อนทำ hash ทำให้เหตุการณ์คนละรายการที่มี signature เดียวกันแชร์ผลวิเคราะห์ได้ โดยยังเลือก incident แต่ละรายการแยกกันได้

## 3. Diagnosis และ Privacy Boundary

### 3.1 Offline Diagnosis

`backend/ai_engine/offline.py` ใช้ exception/category/hang metadata ที่ parser เตรียมไว้ สร้าง `AIDiagnosisResult` ที่มีโครงสร้างเดียวกับ Gemini:

- `simple_summary`
- `technical_explanation`
- `probable_causes`
- `actionable_resolutions` แบ่ง Tier 1–3
- `search_queries`

ดังนั้นระบบยังใช้งานได้ครบแม้ไม่มี network หรือ API key

### 3.2 Gemini adapter

`backend/ai_engine/gemini_analyzer.py` ใช้ `google-genai` และส่ง `AIDiagnosisResult` เป็น `response_schema` เพื่อบังคับรูปแบบ JSON จาก model ก่อนตรวจซ้ำด้วย Pydantic

ลำดับการทำงานของ `DiagnosisService.diagnose()`:

1. คำนวณ `signature_hash`
2. อ่าน cache เมื่อไม่ได้ขอ `force_refresh`
3. เรียก Gemini และ retry ตาม policy
4. validate structured result
5. cache เฉพาะผลที่ validate สำเร็จ
6. หาก Gemini ใช้งานไม่ได้ คืน Offline Diagnosis พร้อม warning

Telemetry projection ใน `prompts.py` ตัด machine name, PID, report ID, full path และข้อมูล host ออกจาก prompt โดยส่งเฉพาะข้อมูลที่จำเป็นต่อ diagnosis

### 3.3 SQLite cache

`backend/database.py` เปิด connection ต่อ operation และตั้ง WAL mode:

~~~text
diagnosis_cache
├─ signature_hash
├─ model
├─ prompt_version
├─ diagnosis_json
└─ created_at
~~~

primary key คือ `(signature_hash, model, prompt_version)` ไม่มี TTL การเปลี่ยน prompt version หรือใช้ `force_refresh` ทำให้วิเคราะห์ผลใหม่ได้ หาก database ใช้งานไม่ได้ service จะวิเคราะห์ต่อและส่ง warning แทนการตอบ 500

## 4. API Layer

`backend/app.py` เป็น orchestration layer และไม่ให้ frontend เรียก extractor แยกหลายครั้งระหว่าง scan:

| Endpoint | Flow |
| --- | --- |
| `/api/system-info` | อ่าน OS/runtime/native/AI/cache readiness |
| `/api/dashboard` | อ่าน Event Log ครั้งเดียว แล้วสร้าง events + stats + extractor metadata |
| `/api/events` | compatibility view จาก dashboard reader |
| `/api/stats` | compatibility KPI view |
| `/api/analyze` | รับ `CrashEvent`, คืน Gemini/cache/offline result |
| `/api/simulate` | รับเฉพาะ `SimulationRequest` ที่เป็น Literal allowlist |

Production serving mount เฉพาะ `frontend/dist` ที่ `/static` และ `/` เสิร์ฟ `dist/index.html` ดังนั้น `src`, `node_modules` และ package metadata ไม่ถูกเปิดจาก server

## 5. Demo Lab และ Process Isolation

`scripts/crash_simulator.py` ไม่รับ arbitrary command แต่ใช้ dictionary `SIMULATION_PAYLOADS` ที่กำหนดไว้ล่วงหน้า แล้วเรียก child process ผ่าน `subprocess.Popen`:

| Type | OS signal ที่ต้องการสาธิต | ผลที่คาดหวัง |
| --- | --- | --- |
| `fatal_exit` | Universal C Runtime abort | Event 1000 / `0xc0000409` |
| `access_violation` | native `RaiseException` | Event 1000 / `0xc0000005` |
| `fail_fast` | `.NET Environment.FailFast()` | Event 1000 / runtime failure |
| `breakpoint` | `Debugger.Break()` | Event 1000 / `0x80000003` |
| `gui_freeze` | blocked GUI message loop | Event 1002 หรือ labelled local fallback |

การจำลองออกแบบเพื่อ demo ระบบ Event Log ไม่ใช่การทดสอบความเสียหายของเครื่องจริง ระบบจึงไม่สร้าง BSOD, ไม่ฆ่า process ของ dashboard และไม่รับคำสั่งจากผู้ใช้โดยตรง

## 6. Frontend Architecture

Frontend อยู่ใน `frontend/src/` และใช้ React hooks โดยไม่มี router หรือ state library ขนาดใหญ่:

- `App.jsx` — application entry
- `components/dashboard.jsx` — shell, command bar, KPI, filters, feed, investigation workspace และ Demo Lab
- `components/ui.jsx` — Button, Card, Tabs, Dialog, Command และ primitives ที่ใช้ร่วมกัน
- `api.js` — same-origin fetch client
- `index.css` — design tokens, layout, responsive และ reduced-motion rules
- `lib/utils.js` — formatting, severity tone, clipboard และ class utilities

ลำดับการใช้งานคือ `System status → KPI → filters → incident feed → selected investigation` รองรับ desktop แบบสองคอลัมน์, tablet แบบเรียงลง และ mobile แบบ list/detail

AI state ที่ UI ต้องแยกให้เห็นคือ not analyzed, loading, Gemini success, cache hit, offline fallback และ retry/error พร้อมคง offline summary ไว้เมื่อ AI ล้มเหลว

## 7. Verification Matrix

ชุดทดสอบปัจจุบันแบ่งเป็น:

| Layer | สิ่งที่ตรวจ |
| --- | --- |
| Parser | crash, hang, missing data และ malformed XML |
| Extractor | native success, fallback และ unavailable |
| Cache/AI | cache round trip, offline path, redaction และ cache hit |
| API | dashboard, static page, offline analyze, validation และ simulator allowlist |
| Simulator | payload allowlist และ native access violation command |
| Frontend | event rendering, command menu, analysis state, KPI และ compact feed |

คำสั่ง verification:

~~~powershell
pytest -q --basetemp .pytest-tmp
cd frontend
npm ci
npm run test -- --run
npm run build
~~~

## 8. Known Limitations

- Event Log schema และ provider details อาจแตกต่างกันเล็กน้อยระหว่าง Windows build จึงมีทั้ง named/positional parsing และ fallback
- Event 1002 สำหรับ GUI window อายุสั้นอาจไม่ถูกเขียนโดย Windows ทุกครั้ง ระบบจะแสดง fallback ที่ติดป้ายอย่างชัดเจนแทน
- Gemini เป็น external dependency และอาจตอบช้า, quota เต็ม หรือ model unavailable; Offline Diagnosis เป็นเส้นทางที่ระบบรองรับอย่างตั้งใจ
- ระบบเป็น local single-user app ไม่มี authentication, remote database หรือ cloud deployment
- diagnosis เป็นคำแนะนำเชิงสืบสวน ไม่ใช่ root cause proof และไม่รัน remediation command อัตโนมัติ
