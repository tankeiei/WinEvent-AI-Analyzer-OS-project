# คู่มืออธิบายสถาปัตยกรรมและการทำงานของโค้ดสกัดข้อมูล Crash & Hang Log
## (WinEvent Analyzer - OS Extraction, Diagnosis & Mission Control)

เอกสารฉบับนี้จัดทำขึ้นเพื่ออธิบายรายละเอียดการทำงานของระบบดึงข้อมูล Application Crash (Event ID 1000) และ Application Hang (Event ID 1002) จากระบบปฏิบัติการ Windows โครงสร้างข้อมูลที่สกัดได้ และการทำงานของแต่ละโมดูลในระดับโค้ดอย่างละเอียด

---

## 1. ข้อมูล Crash & Hang Log ที่สกัดออกมาได้ มีอะไรบ้าง? และบอกอะไรเรา?

เมื่อแอปพลิเคชันเกิดข้อผิดพลาด ระบบปฏิบัติการ Windows จะบันทึกเป็น 2 เหตุการณ์หลักใน Event Log (Channel: `Application`):
1. **Event ID 1000 (Application Error / Crash)**: เกิดเมื่อ Process ชน Unhandled Hardware/Software Exception (เช่น Access Violation `0xc0000005`, Breakpoint `0x80000003`)
2. **Event ID 1002 (Application Hang / Freeze)**: เกิดเมื่อหน้าต่างโปรแกรมหยุดประมวลผล Windows Message Loop เกิน 5 วินาที ทำให้ Windows Desktop Window Manager ทำเครื่องหมายเป็น "Not Responding"

โมเดล `CrashEvent` ใน [backend/models.py](backend/models.py) ได้รับการออกแบบให้สกัดข้อมูลสำคัญครบถ้วน:

| ฟิลด์ข้อมูล (Field) | ชนิดข้อมูล | ตัวอย่างค่าจริงที่สกัดได้จากเครื่อง | ความหมายและการนำไปใช้ |
| :--- | :--- | :--- | :--- |
| **`event_type`** | `Literal["CRASH", "HANG"]` | `CRASH` หรือ `HANG` | **ประเภทของเหตุการณ์** แยกชัดเจนระหว่างแอปแครชดับไปเลย หรือแอปค้างไม่ตอบสนอง |
| **`event_id`** | `int` | `1000` หรือ `1002` | หมายเลข Event ID ของระบบปฏิบัติการ Windows |
| **`app_name`** | `str` | `tbs_browser.exe`, `RobloxPlayerBeta.exe` | **ชื่อโปรแกรมที่มีปัญหา** |
| **`app_path`** | `str` | `C:\Users\tanku\AppData\Local\Roblox\...` | **ที่อยู่ไฟล์โปรแกรม** บ่งชี้ว่าโปรแกรมถูกติดตั้งอยู่ที่ใด |
| **`module_name`** | `str` | `qbcore.dll` หรือ `UI Message Loop / Thread` | **โมดูลหรือ DLL ต้นเหตุ** (กรณี Hang จะระบุเป็น UI Thread) |
| **`exception_code`** | `str` | `0x80000003` หรือ `N/A` (กรณี Hang) | **รหัสข้อยกเว้น NTSTATUS** ของระบบปฏิบัติการ |
| **`exception_symbol`** | `str` | `STATUS_BREAKPOINT`, `APPLICATION_HANG` | ชื่อสัญลักษณ์มาตรฐานตาม Windows API |
| **`exception_meaning`**| `str` | `แอปพลิเคชันหยุดตอบสนอง (UI Message Loop Freeze)...` | **คำแปลภาษาไทยเข้าใจง่าย** จากพจนานุกรมออฟไลน์ |
| **`hang_type`** | `str` | `Top level window is idle` | **ลักษณะของการค้าง** เช่น หน้าต่างหลักไม่ยอมตอบสนองคำสั่ง |
| **`fault_offset`** | `str` | `0x0000000002f702f4` | ตำแหน่ง Memory Offset ที่เกิด Crash |
| **`process_id`** | `str` | `0x6748`, `0xb770` | Process ID (PID) ของโปรแกรมในขณะนั้น |
| **`time_created`** | `str` | `2026-09-17T09:18:19.5979836Z` | วันที่และเวลาที่เกิดเหตุการณ์อย่างแม่นยำ |
| **`signature_hash`** | `str` | `50676125f18c64e3b3433249ea88efe9` | ค่าแฮชเอกลักษณ์สำหรับค้นหาผลลัพธ์จากแคช |

---

## 2. แผนผังการทำงานของระบบสกัดข้อมูล (Extraction Pipeline)

```
+-------------------------------------------------------------------------------+
|                            1. TEST & SIMULATION LAYER                         |
|  [scripts/crash_simulator.py]                                                 |
|  - ทดสอบจำลอง Exception (0xc0000005, 0xc0000409, 0x80131623, DebugBreak)     |
|  - ทดสอบจำลอง Message Loop Freeze (Event 1002 Hang) ใน Isolated Process       |
+---------------------------------------+---------------------------------------+
                                        |  (Trigger System Telemetry)
                                        v
+-------------------------------------------------------------------------------+
|                             2. OPERATING SYSTEM                               |
|                  Windows Event Viewer (Channel: Application)                  |
|          Event ID 1000 (Crash)  |  Event ID 1002 (Application Hang)           |
+---------------------------------------+---------------------------------------+
                                        |
                   +--------------------+--------------------+
                   |                                         |
                   v (วิธีหลัก: Native C-API)                 v (วิธีสำรอง: Zero-Dependency)
      [win32evtlog.EvtQuery]                    [PowerShell: Get-WinEvent]
                   |                                         |
                   +--------------------+--------------------+
                                        |
                                        v  Raw XML Payload
+-------------------------------------------------------------------------------+
|                       3. PARSER & DECODER LAYER                               |
|  [backend/extractor/parser.py]                                                |
|  - ลบ XML Namespace เพื่อความเสถียร                                           |
|  - แยกแยะ Event ID 1000 (Crash) และ Event ID 1002 (Hang)                      |
|  - สกัด <EventData> (AppName, ModuleName, ExceptionCode, HangType, ExeFileName) |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                     4. OFFLINE ERROR & HANG DICTIONARY                        |
|  [backend/extractor/error_codes.py]                                           |
|  - ปรับ Format รหัส Hex (เช่น 0x80000003)                                      |
|  - แมปรหัส Exception และ Hang เป็นความหมายภาษาไทยที่มนุษย์เข้าใจง่าย           |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                       5. NORMALIZED DATA MODEL                                |
|  [backend/models.py: CrashEvent]                                              |
|  - ตรวจสอบ Type Safety ด้วย Pydantic v2 (แยกระหว่าง CRASH และ HANG)           |
|  - สร้าง Signature Hash สำหรับเตรียมส่งต่อให้ AI และระบบ Caching             |
+-------------------------------------------------------------------------------+
```

---

## 3. รายละเอียดการทำงานของโค้ดแต่ละโมดูล

### 3.1 `backend/extractor/event_reader.py`
- รองรับการกรองทั้ง `Application Error` (Crash ID 1000, 1001) และ `Application Hang` (Hang ID 1002)
- มีพารามิเตอร์ `event_type`: `"ALL"`, `"CRASH"`, หรือ `"HANG"`
- สามารถใช้ XPath หรือ PowerShell FilterHashtable:
  ```powershell
  Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName=@('Application Error', 'Application Hang'); StartTime=$startTime}
  ```

### 3.2 `backend/extractor/parser.py`
- ตรวจสอบ Event ID:
  - **หากเป็น 1002 (Hang)**: สกัด `<Data Name='ExeFileName'>` เป็น `app_path`, สกัด `<Data Name='HangType'>` เป็น `hang_type`, กำหนด `module_name = 'UI Message Loop / Thread'` และแมปเข้ากับคำอธิบายอาการค้าง
  - **หากเป็น 1000/1001 (Crash)**: สกัด `ModuleName`, `ExceptionCode`, `FaultOffset` ตามขั้นตอนปกติ

### 3.3 `backend/extractor/error_codes.py`
- เพิ่มการวินิจฉัย `APPLICATION_HANG`:
  > *"แอปพลิเคชันหยุดตอบสนอง (UI Message Loop Freeze) หน้าต่างโปรแกรมไม่ตอบสนองต่อระบบ Windows เกินเวลาที่กำหนด (ปกติ 5 วินาที) มักเกิดจาก Deadlock, งานคำนวณหนักใน UI Thread หรือรอ Network/Disk I/O โดยไม่มี Timeout"*

### 3.4 `scripts/crash_simulator.py`
- รองรับการจำลอง 5 โหมดใน process แยก:
  1. `fatal_exit`: สั่ง C `abort()` (Event 1000, รหัส `0xc0000409`)
  2. `access_violation`: สั่ง native access violation (Event 1000, รหัส `0xc0000005`)
  3. `fail_fast`: สั่ง .NET `FailFast()` (Event 1000, รหัส `0x80131623`)
  4. `breakpoint`: สั่ง `Debugger.Break()` (Event 1000, รหัส `0x80000003`)
  5. `gui_freeze`: จำลองเปิดหน้าต่าง GUI ที่หยุดตอบสนอง (พฤติกรรม Event 1002)
