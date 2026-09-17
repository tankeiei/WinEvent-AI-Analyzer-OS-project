# WinEvent AI Analyzer

> **ระบบวิเคราะห์และแก้ไขปัญหาแอปพลิเคชันแครชด้วย Windows Event Log และ AI**  
> *A modern Windows Application Crash Diagnosis and Troubleshooting assistant powered by Generative AI.*

---

## 📌 บทนำ (Overview)

เมื่อเกิดเหตุการณ์แอปพลิเคชันขัดข้อง (Crash), ค้าง (Freeze) หรือปิดตัวกะทันหันบน Windows ข้อมูลทางเทคนิคจะถูกบันทึกลงใน **Windows Event Log** อัตโนมัติ (Event ID 1000 และ 1001) ซึ่งมักเต็มไปด้วยรหัสทางเทคนิคระดับลึก (เช่น Exception Code `0xc0000005`, Faulting Module `ntdll.dll`) ทำให้เข้าใจและแก้ไขได้ยาก

**WinEvent AI Analyzer** ทำหน้าที่เป็นสะพานเชื่อมระหว่างระบบปฏิบัติการและผู้ใช้งาน โดยดึงข้อมูล Telemetry ทางเทคนิคมาแปลเป็นภาษาที่เข้าใจง่าย (Tech-to-Human Translation) พร้อมวิเคราะห์สาเหตุและเสนอแนวทางแก้ไขเป็นขั้นตอนผ่าน Google Gemini AI

---

## 🏛️ สถาปัตยกรรมระบบ (Architecture)

1. **OS & Telemetry Layer**
   - ดึงข้อมูลจาก Windows Event Log (Channel: `Application`)
   - กรอง Event ID `1000` (Application Error) และ `1001` (Windows Error Reporting)
   - สกัด App Name, Module, Exception Code, Memory Offset, Timestamp
   - ใช้ `pywin32` Native API พร้อมกลไก PowerShell Fallback

2. **Core Engine & Intelligence**
   - Pydantic Telemetry Normalizer
   - Offline Fallback Dictionary (พจนานุกรมรหัส Win32 / NTSTATUS)
   - Google Gemini AI Engine สำหรับการวินิจฉัยเชิงลึก
   - Local SQLite Cache จัดเก็บผลวิเคราะห์ซ้ำตาม Signature เพื่อประหยัด API Token

3. **User Interface & Dashboard**
   - FastAPI Backend Server
   - Premium Modern Dark Dashboard (HTML5, Vanilla CSS3, JavaScript)
   - ไทม์ไลน์ประวัติ Crash, ตัวกรองช่วงเวลา, Checklist วิธีแก้ปัญหา, แหล่งค้นคว้าอ้างอิง

---

## 🚀 เอกสารเพิ่มเติม

- ศึกษาแผนการพัฒนาและรายละเอียดเชิงลึกทั้งหมดได้ที่ [plan.md](plan.md)
