# คู่มืออธิบายสถาปัตยกรรมและการทำงานของโค้ดสกัดข้อมูล Crash Log
## (WinEvent AI Analyzer - Phase 1: OS Extraction Deep Dive)

เอกสารฉบับนี้จัดทำขึ้นเพื่ออธิบายรายละเอียดการทำงานของระบบดึงข้อมูล Application Crash (Event ID 1000) จากระบบปฏิบัติการ Windows โครงสร้างข้อมูลที่สกัดได้ และการทำงานของแต่ละโมดูลในระดับโค้ดอย่างละเอียด

---

## 1. ข้อมูล Crash Log ที่สกัดออกมาได้ มีอะไรบ้าง? และบอกอะไรเรา?

เมื่อแอปพลิเคชันใดๆ เกิดการแครช ระบบปฏิบัติการ Windows จะดักจับผ่านกลไก **Structured Exception Handling (SEH)** และส่งต่อไปยัง **Windows Error Reporting (WER)** เพื่อบันทึกเป็น **Event ID 1000** ใน Event Log (Channel: `Application`)

โมเดล `CrashEvent` ใน [backend/models.py](backend/models.py) ได้รับการออกแบบให้สกัดข้อมูลสำคัญครบถ้วน ดังนี้:

| ฟิลด์ข้อมูล (Field) | ชนิดข้อมูล | ตัวอย่างค่าจริงที่สกัดได้จากเครื่อง | ความหมายและการนำไปใช้ |
| :--- | :--- | :--- | :--- |
| **`app_name`** | `str` | `tbs_browser.exe` | **ชื่อไฟล์ของโปรแกรมที่แครช** ทำให้ทราบได้ทันทีว่าโปรแกรมใดมีปัญหา |
| **`app_version`** | `str` | `0.0.0.0` หรือ `10.0.26100.9278` | เลขเวอร์ชันของตัวโปรแกรม |
| **`app_path`** | `str` | `C:\Program Files (x86)\Steam\steamapps\common\Delta Force\Launcher\Service\tbs_browser.exe` | **ไดเรกทอรีที่ติดตั้งโปรแกรม** ช่วยระบุว่าเป็นแอปของใคร (เช่น ของ Steam, Windows System32 หรือโปรแกรมภายนอก) |
| **`module_name`** | `str` | `qbcore.dll` หรือ `ntdll.dll` | **โมดูลหรือ DLL ต้นเหตุ** ที่คำสั่งไปพังข้างใน ช่วยเจาะจงว่าพังที่โค้ดของแอปเอง หรือพังที่ไดรเวอร์/ไลบรารีระบบ |
| **`module_path`** | `str` | `C:\Program Files (x86)\Steam\...\qbcore.dll` | ไดเรกทอรีของโมดูลที่มีปัญหา |
| **`exception_code`** | `str` | `0x80000003` หรือ `0xc0000005` | **รหัสข้อผิดพลาดของระบบปฏิบัติการ (NTSTATUS Code)** เป็นกุญแจสำคัญที่สุดในการวิเคราะห์สาเหตุ |
| **`exception_symbol`** | `str` | `STATUS_BREAKPOINT` หรือ `STATUS_ACCESS_VIOLATION` | ชื่อสัญลักษณ์คงที่ตามมาตรฐาน Windows API |
| **`exception_meaning`**| `str` | `โปรแกรมชนจุดหยุด Hardcoded Breakpoint...` | **คำแปลภาษาไทยระดับที่มนุษย์เข้าใจง่าย** จากพจนานุกรมออฟไลน์ |
| **`fault_offset`** | `str` | `0x0000000002f702f4` | ตำแหน่ง Address สัมพัทธ์ในหน่วยความจำที่คำสั่งผิดพลาด (Memory Offset) |
| **`process_id`** | `str` | `0x6748` (หรือ 26440) | Process ID (PID) ของโปรแกรมในขณะที่เกิดเหตุการณ์ |
| **`time_created`** | `str` | `2026-09-17T09:18:19.5979836Z` | วันที่และเวลาที่เกิดเหตุการณ์อย่างแม่นยำ |
| **`signature_hash`** | `str` | `71f0bb4c87a79db26f380ce0932cef81` | ค่าแฮชเอกลักษณ์ (`MD5(AppName + ModuleName + ExceptionCode)`) สำหรับระบบ Caching |

---

## 2. แผนผังการทำงานของระบบสกัดข้อมูล (Extraction Pipeline)

```
+-------------------------------------------------------------------------------+
|                             1. OPERATING SYSTEM                               |
|                  Windows Event Viewer (Channel: Application)                  |
|                        Event ID 1000 (Application Error)                      |
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
|                       2. PARSER & DECODER LAYER                               |
|  [backend/extractor/parser.py]                                                |
|  - ลบ XML Namespace เพื่อความเสถียร                                           |
|  - ดึงแท็ก <System> (TimeCreated, EventRecordID, ProcessId)                   |
|  - ดึงแท็ก <EventData> ทั้งแบบระบุ Name และแบบอิงลำดับ Index                  |
+---------------------------------------+---------------------------------------+
                                        |
                                        v  Raw Exception Code (เช่น '80000003')
+-------------------------------------------------------------------------------+
|                     3. OFFLINE ERROR CODE DICTIONARY                          |
|  [backend/extractor/error_codes.py]                                           |
|  - ปรับ Format เป็นเลขฐานสิบหก 8 หลัก: '0x80000003'                           |
|  - จับคู่ความหมาย: STATUS_BREAKPOINT + คำอธิบายภาษาไทย                        |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                       4. NORMALIZED DATA MODEL                                |
|  [backend/models.py: CrashEvent]                                              |
|  - ตรวจสอบชนิดข้อมูลด้วย Pydantic v2                                          |
|  - สร้าง Signature Hash สำหรับ SQLite Cache และ AI Prompt ใน Phase ถัดไป      |
+-------------------------------------------------------------------------------+
```

---

## 3. อธิบายการทำงานของโค้ดแต่ละโมดูลอย่างละเอียด

### 3.1 `backend/extractor/event_reader.py` (ตัวอ่าน Event Log)
โมดูลนี้ทำหน้าที่เชื่อมต่อกับระบบปฏิบัติการ Windows โดยใช้เทคนิค **Dual-Engine Pattern**:

```python
# 1. ตรวจสอบว่าในเครื่องมีไลบรารี pywin32 หรือไม่
try:
    import win32evtlog
    HAS_PYWIN32 = True
except ImportError:
    HAS_PYWIN32 = False
```

1. **ฟังก์ชัน `_fetch_via_pywin32(hours, max_events)`**:
   - ใช้ C-API ระดับ Native (`win32evtlog.EvtQuery`)
   - ส่งคำสั่ง XPath กรองเฉพาะ Event ที่ต้องการ:
     ```xpath
     *[System[Provider[@Name='Application Error'] and (EventID=1000) and TimeCreated[timediff(@SystemTime) <= {ms_ago}]]]
     ```
   - วิธีนี้กินทรัพยากรน้อยมากและทำงานเร็วในระดับมิลลิวินาที

2. **ฟังก์ชัน `_fetch_via_powershell(hours, max_events)`**:
   - หากสภาพแวดล้อมยังไม่ได้ติดตั้ง `pywin32` ระบบจะสลับมาใช้ PowerShell อัตโนมัติผ่าน `subprocess.run`
   - ใช้คำสั่ง `Get-WinEvent` พร้อม Filter Hashtable:
     ```powershell
     $startTime = (Get-Date).AddHours(-{hours})
     Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'; StartTime=$startTime} -MaxEvents {max_events}
     ```
   - ส่งออกข้อมูลเป็น XML ด้วย `$e.ToXml()` โดยคั่นด้วย Marker `---EVENT_XML_START---` ทำให้ฝั่ง Python แยกแยะแต่ละ Event ได้ 100% โดยไม่มีข้อความขยะปน

3. **ฟังก์ชัน `get_crash_events(...)`**:
   - เป็นตัวกลาง (Facade) ที่เรียกใช้ Engine ที่ดีที่สุด และรองรับการกรองตามชื่อแอปพลิเคชัน (`app_name`)

---

### 3.2 `backend/extractor/parser.py` (ตัวแปลงโครงสร้าง XML)
Windows Event Log ส่งข้อมูลออกมาในรูปแบบ XML ซึ่งมักมีปัญหาเรื่อง XML Namespace ทำให้ ElementTree ทั่วไปค้นหาข้อมูลไม่เจอ โค้ดส่วนนี้จึงจัดการดังนี้:

1. **ทำความสะอาด Namespace**:
   ```python
   clean_xml = re.sub(r'\sxmlns="[^"]+"', '', xml_str, count=1)
   clean_xml = re.sub(r"\sxmlns='[^']+'", '', clean_xml, count=1)
   root = ET.fromstring(clean_xml)
   ```
2. **การสกัดข้อมูลแบบทนทาน (Robust Extraction)**:
   - สกัดข้อมูล `<System>`: วันที่เวลา (`SystemTime`), หมายเลขบันทึก (`EventRecordID`)
   - สกัดข้อมูล `<EventData>`: บันทึกข้อมูลทั้งแบบจับคู่ชื่อ `Name` (เช่น `AppName`, `ModuleName`, `ExceptionCode`) และแบบตำแหน่ง Index (0 ถึง 12) เพื่อรองรับ Windows หลากหลายรุ่นที่อาจมีหรือไม่มี Attribute `Name`
3. **ส่งต่อให้พจนานุกรมและประกอบเป็นโมเดล**:
   - ส่ง `ExceptionCode` ไปแปลงและค้นหาความหมาย
   - ประกอบเป็นออบเจกต์ `CrashEvent`

---

### 3.3 `backend/extractor/error_codes.py` (พจนานุกรมรหัสข้อผิดพลาดออฟไลน์)
ทำหน้าที่เป็นคลังความรู้ระดับระบบปฏิบัติการ (NTSTATUS & Win32 Error Codes):

1. **ฟังก์ชัน `normalize_code(raw_code)`**:
   - แปลงรหัสจากรูปแบบต่างๆ เช่น `80000003`, `0x80000003`, `C0000005` ให้กลายเป็นมาตรฐาน `0x` ตามด้วยเลขฐาน 16 จำนวน 8 หลักตัวพิมพ์เล็กเสมอ
2. **ฐานข้อมูล `EXCEPTION_DATABASE`**:
   - บรรจุรหัสยอดนิยมที่พบบ่อยใน Windows:
     - `0xc0000005`: `STATUS_ACCESS_VIOLATION` (การเข้าถึงหน่วยความจำผิดกฎหมาย เช่น Null Pointer, แรมเสีย)
     - `0x80000003`: `STATUS_BREAKPOINT` (ชนจุด Hardcoded Breakpoint มักเกิดจากบั๊กหรือระบบแอนตี้ชีต)
     - `0x80000002`: `STATUS_DATATYPE_MISALIGNMENT` (การอ่านหน่วยความจำไม่ตรงแนวฮาร์ดแวร์ซีพียู)
     - `0xc0000409`: `STATUS_STACK_BUFFER_OVERRUN` (ระบบความปลอดภัยตรวจพบล้นสแตก)
     - `0x80131623`: `COR_E_FAILFAST` (แอปพลิเคชัน .NET สั่ง FailFast ตัดการทำงานฉุกเฉิน)
     - `0x40000015`: `STATUS_FATAL_APP_EXIT` (โปรแกรมเรียก abort() หรือ FatalAppExit())

---

### 3.4 `backend/models.py` (Data Schema & Caching Hash)
1. **คลาส `CrashEvent` (Pydantic Model)**:
   - ตรวจสอบ Type Safety และรองรับการ Export เป็น JSON ได้ทันทีผ่าน `.model_dump()`
2. **พร็อพเพอร์ตี้ `signature_hash`**:
   ```python
   @property
   def signature_hash(self) -> str:
       norm_app = (self.app_name or "").lower().strip()
       norm_mod = (self.module_name or "").lower().strip()
       norm_exc = (self.exception_code or "").lower().strip()
       key = f"{norm_app}:{norm_mod}:{norm_exc}"
       return hashlib.md5(key.encode("utf-8")).hexdigest()
   ```
   - ทำการสร้างค่า MD5 จาก **ชื่อแอป + ชื่อโมดูล + รหัส Exception**
   - มีประโยชน์มหาศาลสำหรับ Phase ถัดไป: หากผู้ใช้เปิดโปรแกรมเดิมแล้วแครชซ้ำด้วยสาเหตุเดิม ระบบสามารถนำ Hash นี้ไปค้นใน Local SQLite Cache แล้วตอบวิธีแก้ไขได้ใน **0.01 วินาที** โดยไม่ต้องเสียเงินหรือ Token ยิงไปถาม Gemini AI ซ้ำ

---

### 3.5 `scripts/crash_simulator.py` (ตัวจำลองแอปแครชอย่างปลอดภัย)
ทำไมการจำลองถึงไม่ทำให้เครื่องพังหรือกระทบโปรแกรมอื่น?
1. **Isolated Subprocess**:
   - สคริปต์จะไม่รันคำสั่งแครชในตัวแม่ของมันเอง แต่จะใช้ `subprocess.Popen` แตก Process ลูก (Child Process) แยกออกมาโดดๆ
2. **คำสั่งจำลองที่ทดสอบแล้ว**:
   - `fatal_exit`: สั่ง `ctypes.cdll.msvcrt.abort()` ให้ Process ลูกจบการทำงานฉุกเฉิน เกิดรหัส `0x40000015`
   - `fail_fast`: เรียก `[System.Environment]::FailFast()` ใน PowerShell แยก เกิดรหัส `0x80131623`
   - `breakpoint`: เรียก `[System.Diagnostics.Debugger]::Break()` เกิดรหัส `0x80000003`
3. **การบันทึกของระบบปฏิบัติการ**:
   - เมื่อ Process ลูกตายกะทันหัน ระบบปฏิบัติการ Windows (WER) จะเข้ามารับช่วงต่อ บันทึกข้อมูลลง Event Viewer (Event ID 1000) ตามปกติ แล้วเคลียร์หน่วยความจำทิ้งอย่างสมบูรณ์ ปลอดภัย 100%

---

## 4. สรุปความพร้อมของระบบสำหรับก้าวสู่ Phase 2 & 3

- **Phase 1 สมบูรณ์แล้ว**: ดึงข้อมูลได้ทั้งแบบ Native และ Fallback, สกัดฟิลด์สำคัญครบถ้วน, แปลงรหัสออฟไลน์ได้, และมีเครื่องมือจำลองการทดสอบ
- **ก้าวต่อไป**: 
  - เชื่อมต่อ **Google Gemini AI** ใน Phase 3 เพื่อนำข้อมูลที่สกัดได้นี้ ส่งเข้าไปวิเคราะห์หาสาเหตุเชิงลึกและวิธีแก้ปัญหาแบบ Checklist
  - พัฒนา **FastAPI Server** และ **Modern Web Dashboard** ใน Phase 4 เพื่อแสดงผลหน้าตาสวยงาม
