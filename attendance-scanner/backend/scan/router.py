from fastapi import APIRouter, HTTPException, Depends, Form, UploadFile, File
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from supabase import create_client, Client
from config import settings
from auth.utils import get_current_teacher
from ocr import pipeline

router = APIRouter(prefix="/scan", tags=["scan"])


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


# ── New endpoint: receives already-extracted text fields from browser OCR ──
class ScanMatchRequest(BaseModel):
    session_id: str
    year: str
    roll_no: Optional[str] = None
    id_no: Optional[str] = None
    name: Optional[str] = None
    raw_text: str = ""


@router.post("/match")
async def scan_match(
    data: ScanMatchRequest,
    current: dict = Depends(get_current_teacher),
):
    """
    Browser sends OCR-extracted fields (Roll No, ID No, Name).
    Backend matches against Supabase student roster and records attendance.
    No image upload needed — OCR is done client-side via tesseract.js.
    """
    supabase = get_supabase()

    # Nothing usable extracted
    if not data.roll_no and not data.id_no and not data.name:
        return {"status": "no_text", "message": "ID Not Scanned"}

    # Fetch roster for this teacher + year
    roster_result = (
        supabase.table("students")
        .select("*")
        .eq("teacher_id", current["teacher_id"])
        .eq("year", data.year)
        .execute()
    )
    roster = roster_result.data

    if not roster:
        return {
            "status": "no_match",
            "message": "No students found for this year. Add students in Settings.",
        }

    # Match student (roll_no → id_no → name)
    fields = {
        "roll_no": data.roll_no,
        "id_no": data.id_no,
        "name": data.name,
    }
    matched_student, matched_on = pipeline.match_student(fields, roster)

    if not matched_student:
        return {
            "status": "no_match",
            "message": "No Match Found",
            "fields": fields,
            "ocr_text": data.raw_text,
        }

    # Already marked?
    existing = (
        supabase.table("attendance_records")
        .select("id,status")
        .eq("session_id", data.session_id)
        .eq("student_id", matched_student["id"])
        .execute()
    )
    if existing.data and existing.data[0]["status"] in ("present", "present_manual"):
        return {
            "status": "already_marked",
            "message": "Already Marked",
            "student": {
                "id": matched_student["id"],
                "name": matched_student["name"],
                "roll_no": matched_student["roll_no"],
                "photo_url": matched_student.get("photo_url"),
            },
            "matched_on": matched_on,
        }

    # Insert attendance record
    supabase.table("attendance_records").insert({
        "session_id": data.session_id,
        "student_id": matched_student["id"],
        "roll_no": matched_student["roll_no"],
        "status": "present",
        "matched_on": matched_on,
        "scanned_at": datetime.utcnow().isoformat(),
    }).execute()

    # Update session present_count
    present_result = (
        supabase.table("attendance_records")
        .select("id")
        .eq("session_id", data.session_id)
        .in_("status", ["present", "present_manual"])
        .execute()
    )
    supabase.table("attendance_sessions").update(
        {"present_count": len(present_result.data)}
    ).eq("id", data.session_id).execute()

    # Save raw OCR text to student for debugging
    if data.raw_text:
        supabase.table("students").update(
            {"card_reference_text": data.raw_text}
        ).eq("id", matched_student["id"]).execute()

    return {
        "status": "success",
        "message": "Present",
        "student": {
            "id": matched_student["id"],
            "name": matched_student["name"],
            "roll_no": matched_student["roll_no"],
            "photo_url": matched_student.get("photo_url"),
        },
        "matched_on": matched_on,
        "fields": fields,
    }


# ── Legacy endpoint: still accepts image frames (optional fallback) ──
@router.post("/frames")
async def scan_frames(
    session_id: str = Form(...),
    year: str = Form(...),
    frames: List[UploadFile] = File(...),
    current: dict = Depends(get_current_teacher),
):
    """Legacy: receives image frames, does OCR server-side with pytesseract."""
    supabase = get_supabase()

    frame_bytes_list = []
    for frame in frames:
        content = await frame.read()
        if content:
            frame_bytes_list.append(content)

    if not frame_bytes_list:
        return {"status": "no_text", "message": "No frames received"}

    best_frame = pipeline.pick_best_frame(frame_bytes_list)
    ocr_text = pipeline.run_ocr(best_frame)

    if not ocr_text.strip():
        return {"status": "no_text", "message": "ID Not Scanned"}

    fields = pipeline.extract_fields(ocr_text)
    if not any(fields.values()):
        return {"status": "no_text", "message": "ID Not Scanned", "ocr_text": ocr_text}

    # Reuse match logic from /match endpoint
    roster_result = (
        supabase.table("students")
        .select("*")
        .eq("teacher_id", current["teacher_id"])
        .eq("year", year)
        .execute()
    )
    matched_student, matched_on = pipeline.match_student(fields, roster_result.data or [])

    if not matched_student:
        return {"status": "no_match", "message": "No Match Found", "ocr_text": ocr_text}

    existing = (
        supabase.table("attendance_records")
        .select("id,status")
        .eq("session_id", session_id)
        .eq("student_id", matched_student["id"])
        .execute()
    )
    if existing.data and existing.data[0]["status"] in ("present", "present_manual"):
        return {"status": "already_marked", "student": matched_student, "matched_on": matched_on}

    supabase.table("attendance_records").insert({
        "session_id": session_id,
        "student_id": matched_student["id"],
        "roll_no": matched_student["roll_no"],
        "status": "present",
        "matched_on": matched_on,
        "scanned_at": datetime.utcnow().isoformat(),
    }).execute()

    present_result = (
        supabase.table("attendance_records")
        .select("id")
        .eq("session_id", session_id)
        .in_("status", ["present", "present_manual"])
        .execute()
    )
    supabase.table("attendance_sessions").update(
        {"present_count": len(present_result.data)}
    ).eq("id", session_id).execute()

    return {
        "status": "success",
        "message": "Present",
        "student": {
            "id": matched_student["id"],
            "name": matched_student["name"],
            "roll_no": matched_student["roll_no"],
            "photo_url": matched_student.get("photo_url"),
        },
        "matched_on": matched_on,
    }
