from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from supabase import create_client, Client
from config import settings
from auth.utils import get_current_teacher

router = APIRouter(prefix="/sessions", tags=["sessions"])


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class SessionCreate(BaseModel):
    year: str
    course: str
    timetable_id: Optional[str] = None


@router.post("")
async def start_session(data: SessionCreate, current: dict = Depends(get_current_teacher)):
    """Start a new attendance session."""
    supabase = get_supabase()

    # Count students for this year
    students_result = supabase.table("students").select("id").eq("teacher_id", current["teacher_id"]).eq("year", data.year).execute()
    total_students = len(students_result.data)

    # Create session
    result = supabase.table("attendance_sessions").insert({
        "teacher_id": current["teacher_id"],
        "year": data.year,
        "course": data.course,
        "session_date": str(date.today()),
        "total_students": total_students,
        "present_count": 0,
    }).execute()

    return result.data[0]


@router.patch("/{session_id}/stop")
async def stop_session(session_id: str, current: dict = Depends(get_current_teacher)):
    """Stop session: mark remaining students absent, compute final counts."""
    supabase = get_supabase()

    # Verify session ownership
    session_result = supabase.table("attendance_sessions").select("*").eq("id", session_id).eq("teacher_id", current["teacher_id"]).execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_result.data[0]

    # Get all students for this year
    students_result = supabase.table("students").select("id,roll_no,name").eq("teacher_id", current["teacher_id"]).eq("year", session["year"]).execute()
    all_students = students_result.data

    # Get already-recorded students in this session
    records_result = supabase.table("attendance_records").select("student_id").eq("session_id", session_id).execute()
    recorded_ids = {r["student_id"] for r in records_result.data}

    # Insert absent records for unrecorded students
    absent_records = []
    for student in all_students:
        if student["id"] not in recorded_ids:
            absent_records.append({
                "session_id": session_id,
                "student_id": student["id"],
                "roll_no": student["roll_no"],
                "status": "absent",
                "scanned_at": datetime.utcnow().isoformat(),
            })

    if absent_records:
        supabase.table("attendance_records").insert(absent_records).execute()

    # Count present
    present_result = supabase.table("attendance_records").select("id").eq("session_id", session_id).in_("status", ["present", "present_manual"]).execute()
    present_count = len(present_result.data)

    # Update session
    updated = supabase.table("attendance_sessions").update({
        "end_time": datetime.utcnow().isoformat(),
        "present_count": present_count,
        "total_students": len(all_students),
    }).eq("id", session_id).execute()

    return {"message": "Session ended", "session": updated.data[0], "present_count": present_count, "total": len(all_students)}


@router.get("")
async def list_sessions(limit: int = 20, offset: int = 0, current: dict = Depends(get_current_teacher)):
    """List all sessions for this teacher, most recent first."""
    supabase = get_supabase()
    result = supabase.table("attendance_sessions").select("*").eq("teacher_id", current["teacher_id"]).order("session_date", desc=True).order("start_time", desc=True).limit(limit).offset(offset).execute()
    return result.data


@router.get("/{session_id}")
async def get_session_detail(session_id: str, current: dict = Depends(get_current_teacher)):
    """Get full session detail with attendance records sorted by roll_no."""
    supabase = get_supabase()
    session_result = supabase.table("attendance_sessions").select("*").eq("id", session_id).eq("teacher_id", current["teacher_id"]).execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    session = session_result.data[0]

    records_result = supabase.table("attendance_records").select("*, students(name, roll_no, photo_url)").eq("session_id", session_id).order("roll_no").execute()

    return {**session, "records": records_result.data}


@router.patch("/{session_id}/records/{student_id}")
async def manual_mark_present(session_id: str, student_id: str, current: dict = Depends(get_current_teacher)):
    """Manually mark a student as present."""
    supabase = get_supabase()

    # Verify session belongs to teacher
    session_result = supabase.table("attendance_sessions").select("*").eq("id", session_id).eq("teacher_id", current["teacher_id"]).execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get student roll_no
    student_result = supabase.table("students").select("roll_no").eq("id", student_id).execute()
    if not student_result.data:
        raise HTTPException(status_code=404, detail="Student not found")
    roll_no = student_result.data[0]["roll_no"]

    # Upsert record
    existing = supabase.table("attendance_records").select("id").eq("session_id", session_id).eq("student_id", student_id).execute()
    if existing.data:
        supabase.table("attendance_records").update({"status": "present_manual", "scanned_at": datetime.utcnow().isoformat()}).eq("id", existing.data[0]["id"]).execute()
    else:
        supabase.table("attendance_records").insert({
            "session_id": session_id,
            "student_id": student_id,
            "roll_no": roll_no,
            "status": "present_manual",
            "matched_on": "manual",
            "scanned_at": datetime.utcnow().isoformat(),
        }).execute()

    # Update present_count
    present_result = supabase.table("attendance_records").select("id").eq("session_id", session_id).in_("status", ["present", "present_manual"]).execute()
    supabase.table("attendance_sessions").update({"present_count": len(present_result.data)}).eq("id", session_id).execute()

    return {"message": "Marked present manually"}


@router.delete("/{session_id}")
async def delete_session(session_id: str, current: dict = Depends(get_current_teacher)):
    """Delete a session and all its records."""
    supabase = get_supabase()
    session_result = supabase.table("attendance_sessions").select("id").eq("id", session_id).eq("teacher_id", current["teacher_id"]).execute()
    if not session_result.data:
        raise HTTPException(status_code=404, detail="Session not found")
    supabase.table("attendance_sessions").delete().eq("id", session_id).execute()
    return {"message": "Session deleted"}
