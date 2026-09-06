from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from supabase import create_client, Client
from config import settings
from auth.utils import get_current_teacher

router = APIRouter(prefix="/students", tags=["students"])


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class StudentCreate(BaseModel):
    name: str
    roll_no: str
    id_no: Optional[str] = None
    year: str
    photo_url: Optional[str] = None


class StudentUpdate(BaseModel):
    name: Optional[str] = None
    roll_no: Optional[str] = None
    id_no: Optional[str] = None
    year: Optional[str] = None
    photo_url: Optional[str] = None


@router.get("")
async def get_students(year: Optional[str] = None, current: dict = Depends(get_current_teacher)):
    """Get all students for this teacher, optionally filtered by year."""
    supabase = get_supabase()
    query = supabase.table("students").select("*").eq("teacher_id", current["teacher_id"])
    if year:
        query = query.eq("year", year)
    result = query.order("roll_no").execute()
    return result.data


@router.post("")
async def create_student(data: StudentCreate, current: dict = Depends(get_current_teacher)):
    """Add a new student to this teacher's roster."""
    supabase = get_supabase()
    result = supabase.table("students").insert({
        "teacher_id": current["teacher_id"],
        "name": data.name,
        "roll_no": data.roll_no,
        "id_no": data.id_no,
        "year": data.year,
        "photo_url": data.photo_url,
    }).execute()
    return result.data[0]


@router.patch("/{student_id}")
async def update_student(student_id: str, data: StudentUpdate, current: dict = Depends(get_current_teacher)):
    """Update a student record (must belong to this teacher)."""
    supabase = get_supabase()
    # Verify ownership
    existing = supabase.table("students").select("id").eq("id", student_id).eq("teacher_id", current["teacher_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Student not found")
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    result = supabase.table("students").update(update_data).eq("id", student_id).execute()
    return result.data[0]


@router.delete("/{student_id}")
async def delete_student(student_id: str, current: dict = Depends(get_current_teacher)):
    """Delete a student (must belong to this teacher)."""
    supabase = get_supabase()
    existing = supabase.table("students").select("id").eq("id", student_id).eq("teacher_id", current["teacher_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Student not found")
    supabase.table("students").delete().eq("id", student_id).execute()
    return {"message": "Student deleted successfully"}
