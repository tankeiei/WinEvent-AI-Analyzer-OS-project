# WinEvent Analyzer
### Windows Application Crash & Hang Monitoring System with AI-assisted Diagnosis

> **ระบบตรวจจับและวิเคราะห์ Application Crash/Hang จาก Windows Event Log พร้อมระบบ AI ช่วยวินิจฉัย**  
> *An OS-centric telemetry monitoring tool capturing Event IDs 1000, 1001, and 1002 from Windows Event Subsystem, providing human-friendly tech-to-human translation and suggested diagnostics.*

---

## 📌 บทนำและจุดเน้นด้านระบบปฏิบัติการ (OS-Centric Overview)

เมื่อเกิดเหตุการณ์แอปพลิเคชันขัดข้อง (Crash) หรือค้างไม่ตอบสนอง (Freeze/Hang) ระบบปฏิบัติการ Windows จะบันทึกหลักฐานทางเทคนิคระดับลึกไว้ใน **Windows Event Log** (Channel: `Application`):
- **Event ID 1000 (Application Error)**: เกิดจาก Unhandled Hardware/Software Exceptions (เช่น Access Violation `0xc0000005`, Breakpoint `0x80000003`)
- **Event ID 1001 (Windows Error Reporting)**: ข้อมูล Telemetry และ Bucket ID
- **Event ID 1002 (Application Hang)**: เกิดจาก UI Thread ของหน้าต่างโปรแกรมหยุดประมวลผล Windows Message Loop เกิน 5 วินาที

**WinEvent Analyzer** มุ่งเน้นการดึงหลักฐานของระบบปฏิบัติการ (OS Telemetry) มาจัดโครงสร้าง วิเคราะห์รหัสข้อยกเว้น และใช้ Generative AI ทำหน้าที่เป็น **ผู้ช่วยสรุป (AI-Assisted)** แปลข้อมูลเทคนิคให้อยู่ในรูปแบบ **"Possible Causes / Suggested Diagnosis"** พร้อมแนวทางการตรวจสอบที่ผู้ใช้สามารถปฏิบัติตามได้จริง

---

## 🏛️ สถาปัตยกรรมระบบ (Pipeline Flow)

$$\text{Safe Simulator} \longrightarrow \text{Windows Event Log} \longrightarrow \text{Dual Extractor} \longrightarrow \text{Parser} \longrightarrow \text{Error Mapping} \longrightarrow \text{AI Diagnosis} \longrightarrow \text{Dashboard}$$

1. **Test & Simulation**: จำลอง Crash (SEH Exceptions) และ Hang (Message Loop Freeze) อย่างปลอดภัยใน Isolated Process
2. **OS Extraction**: ดึง Event ID 1000, 1001, 1002 ด้วย `pywin32` C-API และ `PowerShell Get-WinEvent` Fallback
3. **Data Normalization**: แปลงโครงสร้าง XML ให้เป็น Pydantic Model (`CRASH` และ `HANG`)
4. **Offline Diagnostics**: พจนานุกรมแปลรหัส NTSTATUS, Win32 Codes, และ Hang Types ออฟไลน์
5. **AI-Assisted Engine**: สรุปอาการแบบ Tech-to-Human และเสนอ Possible Causes (Gemini AI)
6. **Local Dashboard**: หน้าจอแดชบอร์ดตรวจสอบประวัติและดูคำแนะนำ

---

## 🚀 วิธีเปิดใช้งาน Web Dashboard (Quick Start)

### วิธีที่ 1: ดับเบิ้ลคลิกเดียว (แนะนำสำหรับ Windows)
ดับเบิ้ลคลิกที่ไฟล์ **`run.bat`** (หรือพิมพ์คำสั่งใน Terminal):
```powershell
.\run.bat
```
> ระบบจะเริ่มเซิร์ฟเวอร์ FastAPI และเปิดเบราว์เซอร์ไปยัง `http://127.0.0.1:8000` ให้อัตโนมัติทันที

---

### วิธีที่ 2: สตาร์ทผ่านคำสั่ง Python / Uvicorn
```powershell
# ติดตั้งไลบรารีที่จำเป็น (รันครั้งแรก)
pip install -r requirements.txt

# สตาร์ทเซิร์ฟเวอร์
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```
จากนั้นเปิดเว็บเบราว์เซอร์ไปที่: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🧪 การทดสอบรัน Phase 1 (คำสั่ง CLI)

```powershell
# ดูประวัติ Crash และ Hang ล่าสุด
python scripts/test_extractor.py --hours 48 --limit 5

# กรองดูเฉพาะกรณีโปรแกรมค้าง (Application Hang - Event 1002)
python scripts/test_extractor.py --type HANG --hours 720

# กรองดูเฉพาะโปรแกรมแครช (Application Crash - Event 1000)
python scripts/test_extractor.py --type CRASH --hours 48

# ทดสอบจำลอง Crash ปลอดภัย (ไม่กระทบเครื่อง)
python scripts/crash_simulator.py --type fatal_exit
```

---

## 📚 เอกสารเพิ่มเติม
- รายละเอียดแผนการพัฒนา: [plan.md](plan.md)
- คู่มืออธิบายโค้ดและสถาปัตยกรรม: [docs/CODE_EXPLANATION.md](docs/CODE_EXPLANATION.md)
