# โครงการ: WinEvent AI Analyzer (ระบบวิเคราะห์และแก้ไขปัญหาแอปพลิเคชันแครชด้วย Windows Event Log และ AI)

---

## 1. บทนำและที่มาของโครงงาน (Introduction & Background)

ในระบบปฏิบัติการ Windows เมื่อเกิดเหตุการณ์แอปพลิเคชันหยุดทำงานโดยไม่คาดคิด (Application Crash), ค้าง (Freeze), หรือปิดตัวลงอย่างกะทันหัน ระบบปฏิบัติการจะบันทึกข้อมูลทางเทคนิคไว้ใน **Windows Event Log** อัตโนมัติ โดยเฉพาะในหมวดหมู่ **Application Error (Event ID 1000)** และ **Windows Error Reporting (Event ID 1001)**

อย่างไรก็ตาม ข้อมูลเหล่านี้มักอยู่ในรูปแบบรหัสทางเทคนิคระดับลึกของระบบปฏิบัติการ (OS-level telemetry) เช่น:
- รหัสข้อผิดพลาดเชิงตัวเลขฐาน 16 (Exception Code เช่น `0xc0000005`, `0xc0000409`)
- ชื่อโมดูลหรือไลบรารีระบบที่เกิดปัญหา (Faulting Module เช่น `ntdll.dll`, `kernelbase.dll`, `d3d11.dll`)
- แอดเดรสหน่วยความจำ (Fault Offset เช่น `0x00000000000a34b2`)

ข้อมูลดังกล่าวเข้าใจได้ยากมากสำหรับผู้ใช้งานทั่วไป และแม้แต่นักพัฒนาก็ยังต้องใช้เวลาค้นหาในเว็บบอร์ดหรือเอกสารทางเทคนิค

**WinEvent AI Analyzer** จึงถูกออกแบบมาเพื่อทำหน้าที่เป็น "สะพานเชื่อมระหว่างระบบปฏิบัติการและผู้ใช้งาน" โดยดึงข้อมูล Event Log ทางเทคนิคมาแปลเป็นภาษาที่มนุษย์เข้าใจง่าย (Tech-to-Human Translation) ผ่านเทคโนโลยี Generative AI (Google Gemini) พร้อมทั้งสรุปสาเหตุและขั้นตอนการแก้ไขปัญหาอย่างเป็นระบบ

---

## 2. สถาปัตยกรรมระบบ (System Architecture)

ระบบถูกออกแบบตามสถาปัตยกรรม 3 ระดับชั้น (3-Tier Layered Architecture):

```
+-------------------------------------------------------------------------------+
|                             1. OS & TELEMETRY LAYER                           |
|  - Windows Event Viewer (Channel: Application)                                |
|  - Event ID 1000: Application Error (AppName, Module, Exception Code, Offset) |
|  - Event ID 1001: Windows Error Reporting (Bucket ID, Context)                |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                         2. CORE ENGINE & INTELLIGENCE                         |
|  [Extractor]        - pywin32 (win32evtlog.EvtQuery) + PowerShell Fallback    |
|  [Telemetry Parser] - จัดโครงสร้างข้อมูลเป็น Normalized Pydantic Models       |
|  [Offline Database] - พจนานุกรม Win32 / NTSTATUS Codes ภายในเครื่อง           |
|  [Cache Database]   - SQLite บันทึกผลวิเคราะห์ซ้ำตาม Crash Signature          |
|  [AI Engine]        - Google Gemini API (Structured JSON Prompting)           |
|  [Search Linker]    - ตัวสร้างลิงก์ค้นคว้าตรง (Microsoft Docs / StackOverflow)|
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                         3. USER INTERFACE & DASHBOARD                         |
|  [Backend Server]   - FastAPI REST API & Local Server                         |
|  [Dashboard View]   - Modern Clean Dark UI (HTML5, Vanilla CSS3, JS)          |
|  - Left Panel:      Crash History Timeline, Search, Quick Filters (24h/7d)    |
|  - Right Panel:     AI Diagnosis, Actionable Checklist, Raw OS Telemetry,     |
|                     Reference Sources                                         |
+-------------------------------------------------------------------------------+
```

---

## 3. รายละเอียดการทำงาน 3 ส่วนหลัก

### ส่วนที่ 1: การสกัดข้อมูลระดับระบบปฏิบัติการ (OS-Level Data Extraction)
1. **การกรองข้อมูล (Event Filtering)**:
   - สแกนหา Event Log จาก Channel `Application`
   - กรองเฉพาะ `Event ID 1000` (Application Error) และ `Event ID 1001` (Windows Error Reporting)
   - กรองตามช่วงเวลา เช่น 24 ชั่วโมงล่าสุด (ค่าเริ่มต้น), 7 วัน, หรือตามที่ผู้ใช้กำหนด
2. **ข้อมูลสำคัญที่ถูกสกัด**:
   - **Application Name**: ชื่อโปรแกรม เช่น `Photoshop.exe`, `Discord.exe`, `Valorant.exe`
   - **Application Path**: ไดเรกทอรีที่ติดตั้งโปรแกรม
   - **Faulting Module**: โมดูลหรือไฟล์ DLL ที่เกิดข้อผิดพลาด เช่น `ntdll.dll`, `d3d11.dll`, `nvwgf2umx.dll`
   - **Faulting Module Path**: ไดเรกทอรีของโมดูล
   - **Exception Code**: รหัสข้อผิดพลาด เช่น `0xc0000005` (Access Violation), `0xc0000409` (Stack Buffer Overrun)
   - **Fault Offset**: ตำแหน่งออฟเซ็ตในหน่วยความจำที่คำสั่งผิดพลาด
   - **Process ID & Timestamp**: วันที่และเวลาที่เกิดเหตุการณ์
3. **ความทนทานของระบบ (Reliability & Fallback)**:
   - ใช้ `win32evtlog.EvtQuery` เป็นหลัก ซึ่งทำงานเร็วระดับ Native API
   - หากสภาพแวดล้อมไม่รองรับ pywin32 ระบบจะสลับไปใช้คำสั่ง `powershell Get-WinEvent` อัตโนมัติ ทำให้ทำงานได้บนเครื่อง Windows ทุกเครื่อง

---

### ส่วนที่ 2: การประมวลผลและการวินิจฉัยด้วย AI (AI Processing & Intelligence)
1. **พจนานุกรมข้อผิดพลาดออฟไลน์ (Offline Fallback Dictionary)**:
   - บรรจุคำอธิบายของ Win32 Exception และ NTSTATUS Codes ยอดนิยมไว้ในตัวโปรแกรม เพื่อให้ทำงานและแปลผลเบื้องต้นได้แม้ในขณะออฟไลน์
2. **การวินิจฉัยผ่าน Google Gemini AI**:
   - ส่งโครงสร้างข้อมูล Crash Telemetry เข้าสู่โมเดล Gemini ด้วย System Prompt ที่กำหนดบทบาทเป็น "ผู้เชี่ยวชาญการแก้ไขปัญหาระบบปฏิบัติการ Windows (Senior Windows Systems Engineer)"
   - กำหนดรูปแบบการตอบกลับเป็น **Structured JSON** เพื่อความแม่นยำสูง:
     - `simple_summary`: สรุปอาการแบบกระชับ (1-2 ประโยค)
     - `tech_to_human`: คำอธิบายสาเหตุเชิงลึกในภาษาที่เข้าใจง่าย (Tech-to-Human Translation)
     - `probable_causes`: ลิสต์สาเหตุที่เป็นไปได้พร้อมระดับความน่าจะเป็น
     - `actionable_resolutions`: เช็กลิสต์ขั้นตอนการแก้ไขปัญหา โดยเรียงลำดับจากระดับง่ายไปยาก:
       - *ระดับที่ 1 (Quick Fix)*: การรันด้วยสิทธิ์ Administrator, การปิดโหมด Compatibility
       - *ระดับที่ 2 (System Integrity)*: การซ่อมแซม Visual C++ Redistributable, การรันคำสั่ง `sfc /scannow`
       - *ระดับที่ 3 (Advanced Fix)*: การอัปเดตไดรเวอร์การ์ดจอ, การตรวจสอบหน่วยความจำ RAM ด้วย Windows Memory Diagnostic
     - `search_references`: ลิงก์ตรงสำหรับค้นหาข้อมูลเพิ่มเติมในเว็บบอร์ดทางการ เช่น Microsoft Learn, Microsoft Community, StackOverflow
3. **ระบบแคชอัจฉริยะ (Local SQLite Caching)**:
   - สร้างคีย์ Hash จาก `AppName + ModuleName + ExceptionCode`
   - หากผู้ใช้มีโปรแกรมเดิมแครชด้วยโค้ดเดิมซ้ำๆ ระบบจะดึงผลวิเคราะห์จากฐานข้อมูลในเครื่องทันที ทำให้ไม่เปลืองโควตา Token API และตอบสนองได้ในเสี้ยววินาที

---

### ส่วนที่ 3: การออกแบบส่วนติดต่อผู้ใช้ (User Interface & User Experience)
เลือกใช้ **Local Web Dashboard (FastAPI + Modern Web UI)** ซึ่งมีความยืดหยุ่นสูง ดีไซน์สวยงามระดับพรีเมียม และเปิดใช้งานได้ทั้งในเบราว์เซอร์หรือแบบแอปพลิเคชัน:

- **ชุดสีและธีม (Aesthetics)**:
  - Sleek Dark Mode (พื้นหลังโทน Slate/Charcoal ตัดด้วยสีเน้นนีออน เช่น Cyan, Indigo, Rose สำหรับสถานะข้อผิดพลาด)
  - Glassmorphism & Micro-animations สำหรับการโต้ตอบที่นุ่มนวล
- **การจัดวางหน้าจอ (Two-Column Responsive Layout)**:
  - **คอลัมน์ซ้าย: Crash Timeline List**:
    - แถบค้นหาโปรแกรม/รหัส Error
    - ปุ่มเลือกช่วงเวลา (24 ชั่วโมง, 7 วัน, ทั้งหมด)
    - ปุ่ม "Scan Now" พร้อมเอฟเฟกต์แอนิเมชันสถานะการสแกน
    - รายการประวัติแอปพลิเคชันที่แครช เรียงตามเวลาล่าสุด พร้อม Badge สีกำกับความรุนแรง
  - **คอลัมน์ขวา: Analysis & Resolution Panel**:
    - **ส่วนที่ 1 - AI Diagnosis Card**: การวิเคราะห์สาเหตุและคำอธิบายภาษาคน
    - **ส่วนที่ 2 - Actionable Resolution Checklist**: การ์ดขั้นตอนการแก้ไขปัญหา มีกล่อง Checkbox ให้ผู้ใช้ติ๊กเมื่อทำตามแต่ละขั้นตอนสำเร็จ พร้อมปุ่มกดคัดลอกคำสั่ง (Copy Command)
    - **ส่วนที่ 3 - OS Raw Telemetry**: ตารางแสดงข้อมูลดิบจาก Event Viewer ที่จัดระเบียบไว้อย่างสวยงาม สามารถคลิกพับเก็บหรือเปิดดูได้
    - **ส่วนที่ 4 - Community & Documentation Links**: ปุ่มลิงก์ภายนอกสำหรับเปิดอ่านวิธีแก้ปัญหาเพิ่มเติม

---

## 4. โครงสร้างไฟล์ในโครงการ (Project File Structure)

```text
OS project/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # API Server (FastAPI) และ Routing
│   ├── config.py                # การจัดการการตั้งค่าและตัวแปรสภาพแวดล้อม
│   ├── database.py              # SQLite Data Access Layer และ Caching
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── event_reader.py      # ดึง Event Log ด้วย pywin32 และ PowerShell
│   │   ├── parser.py            # สกัด XML เป็น Data Model
│   │   └── error_codes.py       # ฐานข้อมูลรหัสข้อผิดพลาด Windows ออฟไลน์
│   └── ai_engine/
│       ├── __init__.py
│       ├── gemini_analyzer.py   # เชื่อมต่อ Gemini API
│       └── prompts.py           # System Prompts และ Output Schemas
├── frontend/
│   ├── index.html               # โครงสร้างหน้าเว็บหลัก
│   ├── css/
│   │   └── style.css            # ดีไซน์ Dark Mode, Glassmorphism, Responsive
│   └── js/
│       └── app.js               # Logic หน้าบ้าน, การดึง API, จัดการ State
├── scripts/
│   ├── run.bat                  # สคริปต์เปิดแอปพลิเคชันในคลิกเดียว
│   └── crash_simulator.py      # สคริปต์ทดสอบจำลองแอปแครชอย่างปลอดภัย
├── requirements.txt             # ไลบรารี Python ที่ต้องใช้
├── plan.md                      # เอกสารแผนงานฉบับนี้
└── README.md                    # เอกสารคู่มือการติดตั้งและใช้งาน
```

---

## 5. แผนการดำเนินงานและขั้นตอนการพัฒนา (Phase-by-Phase Plan)

| เฟส (Phase) | รายละเอียดงาน | ผลลัพธ์ที่ได้ |
| :--- | :--- | :--- |
| **Phase 1: OS Extraction** | เขียนโมดูลดึง Event ID 1000/1001 จาก Windows Event Viewer ด้วย `pywin32` พร้อม fallback `PowerShell` | ดึงข้อมูลแครชย้อนหลัง 24 ชม. ออกมาเป็น JSON ได้อย่างสมบูรณ์ |
| **Phase 2: Error Mapping & Simulator** | สร้างพจนานุกรม Win32/NTSTATUS Codes และเขียน `crash_simulator.py` สำหรับทดสอบ | ตรวจสอบรหัสแครชพื้นฐานได้แบบออฟไลน์ และมีตัวจำลองเพื่อทดสอบระบบ |
| **Phase 3: AI Engine & Caching** | พัฒนาตัวเชื่อมต่อ Gemini API ออกแบบ Prompt ให้ได้คำอธิบายภาษาคนและวิธีแก้แบบ Checklist พร้อมทำระบบ SQLite Cache | ระบบ AI วิเคราะห์สาเหตุและวิธีแก้ปัญหาได้แม่นยำ พร้อมแคชข้อมูลลดการใช้ API |
| **Phase 4: Backend API & UI** | พัฒนา FastAPI Server และหน้าจอ Dashboard แบบ Clean Modern Dark UI เชื่อมต่อทุกส่วนเข้าด้วยกัน | ผู้ใช้เปิดหน้าเว็บ กดสแกน และดูผลการวิเคราะห์แบบแบ่ง 2 ฝั่งได้อย่างสะดวก |
| **Phase 5: Verification & Report** | ทดสอบระบบแบบ End-to-End, สร้างสคริปต์ `run.bat`, และจัดทำเอกสารสรุปโครงการ | ระบบพร้อมใช้งานและมีข้อมูลครบถ้วนสำหรับทำรูปเล่มรายงานวิชา OS |

---

## 6. ความโดดเด่นของโครงการสำหรับวิชา Operating System

1. **การประยุกต์ใช้กลไกของ OS จริง**: ใช้งานและทำความเข้าใจระบบ Windows Event Logging, Structured Exception Handling (SEH) และ Error Codes (NTSTATUS)
2. **การแก้ปัญหาจริงของผู้ใช้ (Real-World Utility)**: แก้ปัญหาที่ผู้ใช้ทั่วไปอ่าน Error Code ไม่เข้าใจ โดยเปลี่ยนเป็นขั้นตอนแก้ไขที่จับต้องได้
3. **การผสานเทคโนโลยีสมัยใหม่**: ผนวก low-level OS data เข้ากับ high-level Generative AI ได้อย่างลงตัว
4. **ความน่าเชื่อถือและความเสถียร (Fault Tolerance)**: มีทั้ง Offline Error Code Fallback, Dual-method Log Extraction (pywin32 + PowerShell), และระบบ Local Caching เพื่อประสิทธิภาพสูงสุด
