"""Offline dictionary of Windows NTSTATUS and Win32 exception codes."""

from typing import Dict, Tuple

# Maps normalized hex code (lowercase, with 0x) to (Symbol, Thai Explanation)
EXCEPTION_DATABASE: Dict[str, Tuple[str, str]] = {
    "0xc0000005": (
        "STATUS_ACCESS_VIOLATION",
        "โปรแกรมพยายามเข้าถึง (อ่าน/เขียน/รัน) ในพื้นที่หน่วยความจำที่ไม่มีสิทธิ์เข้าถึง เช่น Null Pointer หรือหน่วยความจำถูกปล่อยไปแล้ว (Use-After-Free)"
    ),
    "0x80000003": (
        "STATUS_BREAKPOINT",
        "โปรแกรมชนจุดหยุด (Hardcoded Breakpoint) หรือเงื่อนไข Assertion ในโค้ดล้มเหลว มักพบในโค้ดดีบั๊กหรือระบบตรวจสอบการโกงเกม (Anti-Cheat)"
    ),
    "0x80000002": (
        "STATUS_DATATYPE_MISALIGNMENT",
        "ซีพียูตรวจพบการเข้าถึงข้อมูลในหน่วยความจำที่ไม่ตรงตามขนาด Alignment ของฮาร์ดแวร์"
    ),
    "0xc0000409": (
        "STATUS_STACK_BUFFER_OVERRUN",
        "ระบบรักษาความปลอดภัยของ Windows ตรวจพบการเขียนทับ Buffer เกินขอบเขตของ Stack เพื่อป้องกันการโจมตี (Stack Smashing) ระบบจึงสั่งบังคับปิดโปรแกรมทันที"
    ),
    "0xc00000fd": (
        "STATUS_STACK_OVERFLOW",
        "หน่วยความจำ Stack ล้นจากการเรียกฟังก์ชันซ้อนกันไม่สิ้นสุด (Infinite Recursion) หรือการจัดสรรอาเรย์ขนาดใหญ่เกินไปในโลคอลสแตก"
    ),
    "0xc000001d": (
        "STATUS_ILLEGAL_INSTRUCTION",
        "ซีพียูพบคำสั่งเครื่องที่ไม่รองรับหรือไม่รู้จัก (เช่น คำสั่ง AVX2/AVX-512 บนซีพียูรุ่นเก่า หรือโค้ดไบนารีในแรมเสียหาย)"
    ),
    "0xc0000374": (
        "STATUS_HEAP_CORRUPTION",
        "หน่วยความจำ Heap เสียหาย มักเกิดจากบั๊กจัดการ Memory ในไลบรารี C/C++ เช่น เขียนเกินขนาดบล็อก Heap หรือการคืนหน่วยความจำซ้ำ (Double Free)"
    ),
    "0xc0000025": (
        "STATUS_NONCONTINUABLE_EXCEPTION",
        "เกิดข้อผิดพลาดร้ายแรงที่ไม่สามารถดำเนินคำสั่งต่อได้ แต่โปรแกรมพยายามฝืนรันต่อ ระบบปฏิบัติการจึงตัดการทำงานทันที"
    ),
    "0xc0000094": (
        "STATUS_INTEGER_DIVIDE_BY_ZERO",
        "การหารตัวเลขจำนวนเต็มด้วยศูนย์ในระดับคำสั่งซีพียู"
    ),
    "0xc000008c": (
        "STATUS_ARRAY_BOUNDS_EXCEEDED",
        "การเข้าถึงสมาชิกอาร์เรย์นอกขอบเขตที่ฮาร์ดแวร์กำหนด"
    ),
    "0xc000027b": (
        "STATUS_STOWED_EXCEPTION",
        "ข้อผิดพลาดภายในของแอปพลิเคชันประเภท Modern Windows App (UWP / Windows App SDK)"
    ),
    "0xe06d7363": (
        "MS_CPP_EXCEPTION",
        "เกิดข้อผิดพลาด (C++ Exception) ในโปรแกรมที่คอมไพล์ด้วย Microsoft Visual C++ ที่ไม่ได้ถูกเขียนคำสั่ง catch ดักจับไว้"
    ),
    "0xe0434352": (
        "CLR_EXCEPTION",
        "เกิดข้อผิดพลาดรุนแรงที่ไม่ถูกดักจับในระบบ Microsoft .NET Framework / CLR (Common Language Runtime)"
    ),
    "0x80131623": (
        "COR_E_FAILFAST",
        "แอปพลิเคชันตระกูล .NET เรียกใช้ Environment.FailFast() เพื่อตัดการทำงานทันทีเนื่องจากตรวจพบสถานะวิกฤตที่ไม่สามารถดำเนินโปรแกรมต่อได้อย่างปลอดภัย"
    ),
    "0x40000015": (
        "STATUS_FATAL_APP_EXIT",
        "โปรแกรมสั่งจบการทำงานฉุกเฉินผ่านการเรียก abort() หรือ FatalAppExit() เนื่องจากตรวจพบบั๊กหรือเงื่อนไขข้อผิดพลาดร้ายแรงที่ไม่สามารถกู้คืนได้"
    ),
}


def normalize_code(raw_code: str) -> str:
    """Normalizes an exception code string to standard 8-char hex format (e.g. '0xc0000005')."""
    if not raw_code:
        return "0x00000000"
    
    code = raw_code.strip().lower()
    if code.startswith("0x"):
        code = code[2:]
    
    # Pad to 8 hex digits if needed
    code = code.zfill(8)
    return f"0x{code}"


def lookup_exception(code: str) -> Tuple[str, str]:
    """
    Looks up an exception code in the offline database.
    Returns (Symbol, Meaning). If unknown, returns ('UNKNOWN_EXCEPTION', generic text).
    """
    norm = normalize_code(code)
    if norm in EXCEPTION_DATABASE:
        return EXCEPTION_DATABASE[norm]
    
    return (
        "UNKNOWN_EXCEPTION",
        f"รหัสข้อผิดพลาดเฉพาะ ({norm}) ที่ไม่ได้อยู่ในฐานข้อมูลพจนานุกรมออฟไลน์ ต้องให้ AI วินิจฉัยเพิ่มเติม"
    )
