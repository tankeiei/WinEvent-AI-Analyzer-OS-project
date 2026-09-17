# โครงการ: WinEvent Analyzer
## (Windows Application Crash & Hang Monitoring System with AI-assisted Diagnosis)
### ระบบตรวจจับและวิเคราะห์ Application Crash/Hang จาก Windows Event Log พร้อมระบบ AI ช่วยวินิจฉัย

---

## 1. บทนำและที่มาของโครงงาน (Introduction & Systems Background)

ในระบบปฏิบัติการ Windows เมื่อเกิดเหตุการณ์แอปพลิเคชันหยุดทำงานโดยไม่คาดคิด (Application Crash) หรือหน้าต่างโปรแกรมค้างและหยุดตอบสนอง (Application Freeze / Hang) ระบบปฏิบัติการจะบันทึกข้อมูลทางเทคนิคระดับลึกไว้ใน **Windows Event Log** (Channel: `Application`) อัตโนมัติ:
- **Event ID 1000 (Application Error)**: บันทึกข้อมูลเมื่อ Process เกิด Unhandled Hardware/Software Exception ข้อมูลประกอบด้วย Exception Code (เช่น `0xc0000005`, `0x80000003`), Faulting Module (`ntdll.dll`, DLLs), และ Fault Offset ในหน่วยความจำ
- **Event ID 1001 (Windows Error Reporting - WER)**: ข้อมูล Telemetry และ Bucket ID สำหรับรายงานข้อผิดพลาดไปยัง Microsoft
- **Event ID 1002 (Application Hang)**: บันทึกข้อมูลเมื่อ GUI Thread ของแอปพลิเคชันหยุดประมวลผล Windows Message Loop เกินเวลาที่กำหนด (ปกติ 5 วินาที) ทำให้ Desktop Window Manager (DWM) ทำเครื่องหมายหน้าต่างว่าเป็น "Not Responding" พร้อมระบุ `HangType`

ข้อมูลเหล่านี้เป็นหลักฐานระดับลึกของระบบปฏิบัติการ (OS-level Telemetry) ซึ่งมีความสำคัญอย่างยิ่งต่อการดูแลรักษาระบบ แต่ผู้ใช้งานทั่วไปมักอ่านไม่เข้าใจ และแม้แต่นักพัฒนาก็ต้องใช้เวลาค้นหาเอกสารเทคนิค

**WinEvent Analyzer** จึงถูกสร้างขึ้นโดยมี **ระบบปฏิบัติการ Windows เป็นหัวใจหลัก (OS-Centric)** เพื่อดึงข้อมูล telemetry เหล่านี้มาจัดโครงสร้าง วิเคราะห์รหัสข้อยกเว้น (Exception / NTSTATUS) และใช้ Generative AI ทำหน้าที่เป็น **ผู้ช่วยสรุป (AI-assisted)** เพื่อแปลผลเป็นภาษาที่มนุษย์เข้าใจง่าย พร้อมเสนอ **"Possible Causes / Suggested Diagnosis"** และขั้นตอนการตรวจสอบแก้ไขปัญหาอย่างเป็นระบบ

---

## 2. สถาปัตยกรรมระบบ (System Architecture)

ระบบทำงานเป็น Core Pipeline ต่อเนื่อง 6 ขั้นตอน:

```
+-------------------------------------------------------------------------------+
|                            1. TEST & SIMULATION LAYER                         |
|  [scripts/crash_simulator.py]                                                 |
|  - ทดสอบจำลอง Exception (0xc0000005, 0x80131623, 0x40000015, DebugBreak)     |
|  - ทดสอบจำลอง Window Message Loop Freeze (Event 1002 Hang) ใน Isolated Process |
+---------------------------------------+---------------------------------------+
                                        |  (Trigger System Telemetry)
                                        v
+-------------------------------------------------------------------------------+
|                             2. OS & TELEMETRY LAYER                           |
|  - Windows Event Log Subsystem (Channel: Application)                         |
|  - Event ID 1000: Application Error (Crash SEH Exception)                     |
|  - Event ID 1001: Windows Error Reporting (WER Context)                       |
|  - Event ID 1002: Application Hang (UI Message Loop Unresponsive)             |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                          3. CORE EXTRACTION & PARSER                          |
|  [event_reader.py]  - Dual-Engine (win32evtlog Native C-API + PowerShell)    |
|  [parser.py]        - XML Sanitizer & EventData Extractor (Positional/Named)  |
|  [models.py]        - Normalized Pydantic CrashEvent Model (CRASH & HANG)     |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                        4. ERROR CODE & DIAGNOSTIC LAYER                       |
|  [error_codes.py]   - พจนานุกรม Win32 / NTSTATUS Codes และ Hang Diagnostics  |
|                     - แปลงรหัส Hex และระบุความหมายภาษาไทยเบื้องต้นแบบออฟไลน์    |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                         5. AI-ASSISTED DIAGNOSIS ENGINE                       |
|  [ai_engine/]       - Google Gemini API (Structured JSON Prompting)           |
|                     - สรุปอาการ Tech-to-Human Translation                    |
|                     - เสนอ Possible Causes / Suggested Diagnosis (ไม่ฟันธง)  |
|                     - เช็กลิสต์แนวทางตรวจสอบแก้ไขปัญหาแบบเป็นลำดับขั้น          |
|                     - ระบบ SQLite Cache เก็บผลซ้ำตาม Crash Signature (Bonus)  |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                         6. USER INTERFACE & DASHBOARD                         |
|  [FastAPI Server]   - RESTful Endpoint เสิร์ฟข้อมูล Crash & Hang              |
|  [Dashboard UI]     - Modern Dark Interface (Filter 24h/7d, Crash Timeline,   |
|                       Telemetries View, Actionable Checklist)                 |
+-------------------------------------------------------------------------------+
```

---

## 3. ขอบเขตงานแบบแบ่งระยะ (Phase-by-Phase Implementation)

| เฟส (Phase) | รายละเอียดงาน | ผลลัพธ์ที่ได้ |
| :--- | :--- | :--- |
| **Phase 1: OS Extraction & Test Harness** *(เสร็จสมบูรณ์ 100%)* | พัฒนาระบบดึง Event ID 1000, 1001, 1002 จาก Windows Event Log ด้วย Dual-Engine พร้อม Safe Simulator | ดึงประวัติ Crash และ Hang จริงในเครื่องออกมาเป็น JSON ได้สมบูรณ์ |
| **Phase 2: Error Mapping & Diagnostic Normalization** *(เสร็จสมบูรณ์ 100%)* | จัดหมวดหมู่รหัส Win32/NTSTATUS เป็น 6 กลุ่มระบบ ระบุระดับ Severity พร้อม Actionable Checklist ออฟไลน์ และเตรียม Prompt Schema สำหรับ AI | ระบบเข้าใจรหัสทุกกลุ่ม มีเช็กลิสต์แนะนำเบื้องต้น และพร้อมส่งต่อข้อมูลให้ AI ใน Phase 3 |
| **Phase 3: AI-Assisted Diagnosis Engine** | เชื่อมต่อ Gemini API วิเคราะห์อาการแบบ Suggested Diagnosis พร้อมทำ SQLite Cache | ได้รับผลวิเคราะห์ภาษาคนและเช็กลิสต์แนวทางแก้ไขปัญหา |
| **Phase 4: Backend API & Modern Dashboard** | สร้าง FastAPI endpoints และพัฒนาหน้าเว็บ Dashboard สวยงามใช้งานง่าย | ผู้ใช้เปิดหน้าเว็บ กดสแกน และดูผลการวิเคราะห์แบ่งฝั่งได้ทันที |
| **Phase 5: Verification & Report** | ทดสอบ End-to-End เดโมการรันจริง และจัดทำรูปเล่มรายงานวิชา OS | โปรเจกต์พร้อมนำเสนอและส่งอาจารย์ |

---

## 4. จุดเด่นสำหรับวิชา Operating System (OS Highlights)

1. **การใช้งานกลไกของ OS จริง**: ศึกษาและประยุกต์ใช้ Windows Event Logging, Structured Exception Handling (SEH), NTSTATUS Error Codes, และ Windows Message Loop Architecture
2. **เข้าใจทั้งกรณี Crash และ Hang**: ครอบคลุมทั้งโปรแกรมที่ตายเพราะ Memory/CPU Exception (Event 1000) และโปรแกรมที่ค้างเพราะ UI Thread ติดบล็อก (Event 1002)
3. **การทดสอบที่ควบคุมได้ (Controlled Simulation)**: สคริปต์ `crash_simulator.py` แสดงให้เห็นปฏิสัมพันธ์กับ OS ชัดเจน โดยสั่งให้ Process ย่อยเกิดข้อผิดพลาด แล้วให้ OS ดักจับและบันทึก Event Log
4. **ความน่าเชื่อถือสูง**: มีทั้ง Dual-Engine Fallback และการวินิจฉัยออฟไลน์ ทำงานได้บน Windows ทุกเครื่องโดยไม่ต้องติดตั้งโปรแกรมเสริม
