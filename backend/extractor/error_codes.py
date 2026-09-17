"""Offline dictionary of Windows NTSTATUS, Win32 exception codes, and Hang diagnostics.
Categorized into logical OS failure domains with severity ratings and actionable checklists.
"""

from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass


@dataclass
class DiagnosticMetadata:
    symbol: str
    category: str
    category_label: str
    severity: str  # CRITICAL, HIGH, MEDIUM, WARNING
    meaning: str
    suggested_checks: List[str]


# Comprehensive database mapping normalized hex codes or special keys to DiagnosticMetadata
EXCEPTION_DATABASE: Dict[str, DiagnosticMetadata] = {
    # -------------------------------------------------------------
    # 1. MEMORY VIOLATIONS
    # -------------------------------------------------------------
    "0xc0000005": DiagnosticMetadata(
        symbol="STATUS_ACCESS_VIOLATION",
        category="MEMORY_VIOLATION",
        category_label="การจัดการหน่วยความจำ (Memory)",
        severity="CRITICAL",
        meaning="โปรแกรมพยายามเข้าถึง (อ่าน/เขียน/รัน) ในพื้นที่หน่วยความจำที่ไม่มีสิทธิ์เข้าถึง เช่น การอ้างอิง Null Pointer หรือหน่วยความจำถูกทำลาย/คืนระบบไปแล้ว (Use-After-Free)",
        suggested_checks=[
            "ทดสอบรันโปรแกรมด้วยสิทธิ์ Run as Administrator",
            "รันคำสั่ง 'sfc /scannow' ใน Command Prompt เพื่อซ่อมแซมไฟล์ระบบที่เสียหาย",
            "รัน Windows Memory Diagnostic เพื่อตรวจเช็คความสมบูรณ์ของแถบ RAM",
            "อัปเดตไดรเวอร์การ์ดจอ (Display Driver) และไดรเวอร์ชิปเซ็ตเมนบอร์ด"
        ]
    ),
    "0xc0000374": DiagnosticMetadata(
        symbol="STATUS_HEAP_CORRUPTION",
        category="MEMORY_VIOLATION",
        category_label="การจัดการหน่วยความจำ (Memory)",
        severity="CRITICAL",
        meaning="โครงสร้างหน่วยความจำ Heap เสียหาย มักเกิดจากบั๊กในภาษา C/C++ เช่น การเขียนข้อมูลล้นขนาดบัฟเฟอร์ หรือการสั่ง free() หน่วยความจำซ้ำซ้อน (Double Free)",
        suggested_checks=[
            "ตรวจสอบและติดตั้ง Microsoft Visual C++ Redistributable ตัวล่าสุด",
            "อัปเดตแอปพลิเคชันหรือแพตช์แก้ไขจากผู้พัฒนา",
            "ตรวจสอบซอฟต์แวร์เสริม (Add-on/Plugins) ของโปรแกรมที่อาจเข้ากันไม่ได้"
        ]
    ),
    "0xc00000fd": DiagnosticMetadata(
        symbol="STATUS_STACK_OVERFLOW",
        category="MEMORY_VIOLATION",
        category_label="การจัดการหน่วยความจำ (Memory)",
        severity="HIGH",
        meaning="หน่วยความจำ Stack ล้นจากการเรียกใช้ฟังก์ชันซ้อนกันไม่สิ้นสุด (Infinite Recursion) หรือการจัดสรรตัวแปรขนาดใหญ่เกินขีดจำกัดของ Call Stack",
        suggested_checks=[
            "ตรวจสอบว่าไฟล์ข้อมูลที่เปิดมีขนาดใหญ่หรือมีโครงสร้างวนลูปผิดปกติหรือไม่",
            "ตรวจสอบการตั้งค่า Config ของโปรแกรมให้อยู่ในค่าเริ่มต้น (Default Settings)",
            "อัปเดตซอฟต์แวร์เป็นเวอร์ชันล่าสุดเพื่อรับบั๊กฟิกซ์ recursion"
        ]
    ),
    "0xc000008c": DiagnosticMetadata(
        symbol="STATUS_ARRAY_BOUNDS_EXCEEDED",
        category="MEMORY_VIOLATION",
        category_label="การจัดการหน่วยความจำ (Memory)",
        severity="HIGH",
        meaning="คำสั่งซีพียูพยายามเข้าถึงสมาชิกอาร์เรย์นอกขอบเขตที่ฮาร์ดแวร์กำหนด",
        suggested_checks=[
            "ตรวจสอบการตั้งค่าของโปรแกรมว่ามีตัวแปรหรือตัวเลขที่เกินช่วงที่รองรับหรือไม่",
            "แจ้งบั๊กหรือตรวจสอบ release notes ล่าสุดจากผู้พัฒนา"
        ]
    ),

    # -------------------------------------------------------------
    # 2. SECURITY & BUFFER OVERRUNS
    # -------------------------------------------------------------
    "0xc0000409": DiagnosticMetadata(
        symbol="STATUS_STACK_BUFFER_OVERRUN",
        category="SECURITY_BUFFER",
        category_label="ความปลอดภัยของโปรเซส (Security)",
        severity="CRITICAL",
        meaning="กลไกความปลอดภัยของ Windows (Security Cookie /GS) ตรวจพบการเขียนทับ Buffer เกินขอบเขตของ Stack เพื่อป้องกันการโจมตี (Stack Smashing) ระบบจึงสั่งบังคับปิดทันที",
        suggested_checks=[
            "สแกนไวรัสและมัลแวร์ในเครื่องด้วย Windows Security",
            "ตรวจสอบว่ามีโปรแกรม Mod หรือซอฟต์แวร์แทรกแซงโค้ด (Hook/Injection) ทำงานอยู่หรือไม่",
            "ติดตั้งอัปเดตความปลอดภัย Windows Update ล่าสุด"
        ]
    ),
    "0x40000015": DiagnosticMetadata(
        symbol="STATUS_FATAL_APP_EXIT",
        category="SECURITY_BUFFER",
        category_label="การจบการทำงานฉุกเฉิน (Fatal Exit)",
        severity="HIGH",
        meaning="โปรแกรมสั่งจบการทำงานฉุกเฉินผ่านฟังก์ชัน abort() หรือ FatalAppExit() เนื่องจากโค้ดตรวจพบบั๊กหรือสถานะวิกฤตที่ไม่สามารถดำเนินโปรแกรมต่อได้อย่างปลอดภัย",
        suggested_checks=[
            "ตรวจสอบไฟล์ Log หรือ Crash Dump เฉพาะของแอปพลิเคชันในโฟลเดอร์ AppData",
            "ตรวจสอบว่าไฟล์หรือโฟลเดอร์ที่แอปต้องการใช้งานไม่ถูกล็อกหรือลบไป",
            "ทดลองถอนการติดตั้งและลงโปรแกรมใหม่อีกครั้ง (Clean Reinstall)"
        ]
    ),

    # -------------------------------------------------------------
    # 3. RUNTIME & FRAMEWORK ERRORS
    # -------------------------------------------------------------
    "0x80131623": DiagnosticMetadata(
        symbol="COR_E_FAILFAST",
        category="RUNTIME_FRAMEWORK",
        category_label="รันไทม์เฟรมเวิร์ก (.NET/CLR)",
        severity="HIGH",
        meaning="แอปพลิเคชันบน Microsoft .NET สั่งตัดการทำงานฉุกเฉินผ่าน Environment.FailFast() เนื่องจากระบบตรวจพบสภาวะเสี่ยงต่อความสมบูรณ์ของโปรเซส",
        suggested_checks=[
            "ดาวน์โหลดและรัน Microsoft .NET Framework Repair Tool",
            "ตรวจสอบ Windows Event Log ในหมวด '.NET Runtime' เพื่อดู Call Stack ของ Exception",
            "อัปเดตแพ็กเกจ .NET Desktop Runtime เป็นเวอร์ชันล่าสุด"
        ]
    ),
    "0xe0434352": DiagnosticMetadata(
        symbol="CLR_EXCEPTION",
        category="RUNTIME_FRAMEWORK",
        category_label="รันไทม์เฟรมเวิร์ก (.NET/CLR)",
        severity="HIGH",
        meaning="เกิดข้อผิดพลาดรุนแรงระดับ Unhandled Exception ในระบบ Microsoft .NET Framework",
        suggested_checks=[
            "เปิดใช้งาน .NET Framework เวอร์ชันที่แอปพลิเคชันต้องการใน Windows Features",
            "ตรวจสอบการตั้งค่าคอนฟิก `.config` ของโปรแกรมว่าถูกต้องหรือไม่"
        ]
    ),
    "0xe06d7363": DiagnosticMetadata(
        symbol="MS_CPP_EXCEPTION",
        category="RUNTIME_FRAMEWORK",
        category_label="รันไทม์เฟรมเวิร์ก (Visual C++)",
        severity="HIGH",
        meaning="เกิด C++ Exception ในโปรแกรมที่คอมไพล์ด้วย Microsoft Visual C++ ที่ไม่ได้ถูกเขียนโค้ด catch ดักจับไว้",
        suggested_checks=[
            "ติดตั้ง Microsoft Visual C++ Redistributable All-in-One (ทั้ง x86 และ x64)",
            "ตรวจสอบว่ามีไฟล์ DLL ของแอปพลิเคชันสูญหายหรือไม่",
            "ซ่อมแซมไฟล์เกมหรือแอปพลิเคชันผ่านตัวติดตั้ง (Verify Game Files)"
        ]
    ),

    # -------------------------------------------------------------
    # 4. DEBUG & ASSERTION TRAPS
    # -------------------------------------------------------------
    "0x80000003": DiagnosticMetadata(
        symbol="STATUS_BREAKPOINT",
        category="DEBUG_ASSERTION",
        category_label="จุดหยุดตรวจสอบ (Debug/Assert)",
        severity="MEDIUM",
        meaning="โปรแกรมชนจุดหยุด Hardcoded Breakpoint หรือเงื่อนไข Assertion ในโค้ดล้มเหลว มักพบในโค้ดดีบั๊กหรือระบบตรวจสอบความสมบูรณ์ของเกม (Anti-Cheat)",
        suggested_checks=[
            "ตรวจสอบว่ามีโปรแกรมแปลกปลอมที่ระบบ Anti-Cheat อาจสงสัย (เช่น Cheat Engine, Overclocking tools) เปิดอยู่หรือไม่",
            "ปิดโหมด Compatibility Mode ในคุณสมบัติของไฟล์ .exe",
            "ตรวจสอบสิทธิ์การเข้าถึงไฟล์เซฟหรือไฟล์คอนฟิกของเกม"
        ]
    ),
    "0x80000004": DiagnosticMetadata(
        symbol="STATUS_SINGLE_STEP",
        category="DEBUG_ASSERTION",
        category_label="จุดหยุดตรวจสอบ (Debug/Assert)",
        severity="LOW",
        meaning="ระบบตรวจจับคำสั่ง Single-step จากฮาร์ดแวร์ซีพียู มักเกิดจากการรันร่วมกับ Debugger หรือระบบจำลองการทำงาน",
        suggested_checks=[
            "ปิดโปรแกรมดีบั๊กหรือตัวจับเวลาฮาร์ดแวร์ภายนอก",
            "รีสตาร์ทเครื่องเพื่อให้สถานะรีจิสเตอร์ของซีพียูกลับสู่ค่าปกติ"
        ]
    ),

    # -------------------------------------------------------------
    # 5. HARDWARE & CPU INSTRUCTION ERRORS
    # -------------------------------------------------------------
    "0x80000002": DiagnosticMetadata(
        symbol="STATUS_DATATYPE_MISALIGNMENT",
        category="CPU_HARDWARE",
        category_label="ซีพียูและฮาร์ดแวร์ (CPU/Hardware)",
        severity="MEDIUM",
        meaning="ซีพียูตรวจพบการเข้าถึงข้อมูลในหน่วยความจำที่ไม่ตรงตามขนาด Alignment ของฮาร์ดแวร์",
        suggested_checks=[
            "ตรวจสอบความเสถียรของการโอเวอร์คล็อก (Overclock) ทั้ง CPU และ RAM (ลองปิด XMP/EXPO ชั่วคราว)",
            "อัปเดต BIOS / UEFI ของเมนบอร์ดเป็นเวอร์ชันล่าสุด",
            "อัปเดตไดรเวอร์ของระบบปฏิบัติการและ Windows Update"
        ]
    ),
    "0xc000001d": DiagnosticMetadata(
        symbol="STATUS_ILLEGAL_INSTRUCTION",
        category="CPU_HARDWARE",
        category_label="ซีพียูและฮาร์ดแวร์ (CPU/Hardware)",
        severity="HIGH",
        meaning="ซีพียูพบคำสั่งเครื่องที่ไม่รองรับหรือไม่รู้จัก (เช่น คำสั่ง AVX2/AVX-512 บนซีพียูรุ่นเก่า หรือเกิดการเสียหายของไบนารีในหน่วยความจำ)",
        suggested_checks=[
            "ตรวจสอบความต้องการขั้นต่ำของระบบว่าซีพียูรองรับชุดคำสั่งที่แอปต้องการหรือไม่",
            "ตรวจสอบความสมบูรณ์ของไฟล์โปรแกรมและไลบรารี DLL"
        ]
    ),
    "0xc0000094": DiagnosticMetadata(
        symbol="STATUS_INTEGER_DIVIDE_BY_ZERO",
        category="CPU_HARDWARE",
        category_label="ซีพียูและฮาร์ดแวร์ (CPU/Hardware)",
        severity="MEDIUM",
        meaning="คำสั่งทางคณิตศาสตร์ระดับซีพียูเกิดการหารตัวเลขจำนวนเต็มด้วยศูนย์",
        suggested_checks=[
            "ตรวจสอบข้อมูลนำเข้าหรือไฟล์ตั้งค่าที่ส่งให้โปรแกรมคำนวณ",
            "อัปเดตโปรแกรมเป็นรุ่นล่าสุดเพื่อแก้ไขข้อผิดพลาดในการคำนวณ"
        ]
    ),
    "0xc0000025": DiagnosticMetadata(
        symbol="STATUS_NONCONTINUABLE_EXCEPTION",
        category="CPU_HARDWARE",
        category_label="ข้อผิดพลาดระบบ (Non-continuable)",
        severity="CRITICAL",
        meaning="เกิดข้อผิดพลาดร้ายแรงที่ไม่สามารถดำเนินคำสั่งต่อได้ แต่โปรแกรมพยายามฝืนรันต่อ ระบบปฏิบัติการจึงตัดการทำงานทันที",
        suggested_checks=[
            "รีสตาร์ทเครื่องคอมพิวเตอร์เพื่อรีเซ็ตสถานะของระบบ",
            "ตรวจสอบความเสียหายของไดรฟ์จัดเก็บข้อมูลด้วยคำสั่ง 'chkdsk /f'"
        ]
    ),

    # -------------------------------------------------------------
    # 6. APPLICATION HANG (EVENT ID 1002)
    # -------------------------------------------------------------
    "APPLICATION_HANG": DiagnosticMetadata(
        symbol="APPLICATION_HANG",
        category="APPLICATION_HANG",
        category_label="โปรแกรมค้างไม่ตอบสนอง (UI Hang)",
        severity="HIGH",
        meaning="หน้าต่างโปรแกรมหยุดประมวลผล Windows Message Loop เกินเวลาที่กำหนด (ปกติ 5 วินาที) ทำให้ Desktop Window Manager ทำเครื่องหมายว่า 'Not Responding' มักเกิดจาก UI Thread ติดงานประมวลผลหนัก, เกิด Deadlock ระหว่าง Thread, หรือรอ Network/Disk I/O โดยไม่มี Timeout",
        suggested_checks=[
            "ตรวจสอบ Task Manager ดูการใช้งานดิสก์ (Disk 100%) หรือ CPU ที่อาจถูกโปรแกรมอื่นแย่งใช้",
            "ตรวจสอบโปรแกรม Antivirus หรือ Firewall ที่อาจหน่วงการเชื่อมต่อ I/O ของแอป",
            "หลีกเลี่ยงการคลิกซ้ำๆ บนหน้าต่างขณะโปรแกรมกำลังโหลดข้อมูลหนัก",
            "ทดสอบรันด้วยการเชื่อมต่อเครือข่ายอินเทอร์เน็ตที่เสถียร"
        ]
    ),
}


def normalize_code(raw_code: str) -> str:
    """Normalizes an exception code string to standard 8-char hex format (e.g. '0xc0000005')."""
    if not raw_code or raw_code.upper() in ("N/A", "NONE", "UNKNOWN"):
        return "N/A"
    
    code = raw_code.strip().lower()
    if code.startswith("0x"):
        code = code[2:]
    
    code = code.zfill(8)
    return f"0x{code}"


def lookup_diagnostic(code: str) -> DiagnosticMetadata:
    """
    Looks up an exception code or identifier in the offline database.
    Returns DiagnosticMetadata with full category, severity, and suggested checks.
    """
    if code == "APPLICATION_HANG":
        return EXCEPTION_DATABASE["APPLICATION_HANG"]

    norm = normalize_code(code)
    if norm in EXCEPTION_DATABASE:
        return EXCEPTION_DATABASE[norm]
    
    # Generic fallback for unknown codes
    return DiagnosticMetadata(
        symbol="UNKNOWN_EXCEPTION",
        category="UNKNOWN",
        category_label="ข้อผิดพลาดเฉพาะ (Specific Code)",
        severity="MEDIUM",
        meaning=f"รหัสข้อผิดพลาดระดับลึก ({norm}) ที่ไม่ได้อยู่ในฐานข้อมูลพจนานุกรมออฟไลน์เบื้องต้น สามารถใช้ระบบ AI ช่วยวิเคราะห์เพิ่มเติมได้",
        suggested_checks=[
            "ตรวจสอบไฟล์ Log ของตัวแอปพลิเคชันหรือโฟลเดอร์ติดตั้ง",
            "ค้นหาข้อมูลรหัสข้อผิดพลาดและชื่อโมดูลใน Microsoft Learn หรือชุมชนผู้พัฒนา",
            "ทดลองรันโปรแกรมในโหมด Clean Boot เพื่อตัดปัญหาโปรแกรมเบื้องหลังตีกัน"
        ]
    )
