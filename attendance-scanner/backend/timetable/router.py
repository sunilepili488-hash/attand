from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, time
from supabase import create_client, Client
from config import settings
from auth.utils import get_current_teacher

router = APIRouter(prefix="/timetable", tags=["timetable"])


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class TimetableCreate(BaseModel):
    year: str
    course: str
    day_of_week: str
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM"


class TimetableUpdate(BaseModel):
    year: Optional[str] = None
    course: Optional[str] = None
    day_of_week: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


@router.get("")
async def get_timetable(current: dict = Depends(get_current_teacher)):
    """Get all timetable entries for this teacher."""
    supabase = get_supabase()
    result = supabase.table("timetable").select("*").eq("teacher_id", current["teacher_id"]).execute()
    return result.data


@router.get("/today")
async def get_today_timetable(current: dict = Depends(get_current_teacher)):
    """Get today's timetable entries, with is_active flag for the current time slot."""
    supabase = get_supabase()
    today_name = datetime.now().strftime("%A")  # e.g. "Monday"
    result = supabase.table("timetable").select("*").eq("teacher_id", current["teacher_id"]).eq("day_of_week", today_name).execute()

    now = datetime.now().time()
    entries = []
    for entry in result.data:
        start = datetime.strptime(entry["start_time"], "%H:%M:%S").time() if ":" in str(entry["start_time"]) else time.fromisoformat(str(entry["start_time"]))
        end = datetime.strptime(entry["end_time"], "%H:%M:%S").time() if ":" in str(entry["end_time"]) else time.fromisoformat(str(entry["end_time"]))
        entry["is_active"] = start <= now <= end
        entries.append(entry)

    return entries


@router.post("")
async def create_timetable(data: TimetableCreate, current: dict = Depends(get_current_teacher)):
    """Add a new timetable entry."""
    supabase = get_supabase()
    result = supabase.table("timetable").insert({
        "teacher_id": current["teacher_id"],
        "year": data.year,
        "course": data.course,
        "day_of_week": data.day_of_week,
        "start_time": data.start_time,
        "end_time": data.end_time,
    }).execute()
    return result.data[0]


@router.patch("/{entry_id}")
async def update_timetable(entry_id: str, data: TimetableUpdate, current: dict = Depends(get_current_teacher)):
    """Update a timetable entry (must belong to this teacher)."""
    supabase = get_supabase()
    existing = supabase.table("timetable").select("id").eq("id", entry_id).eq("teacher_id", current["teacher_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    update_data = {k: v for k, v in data.dict().items() if v is not None}
    result = supabase.table("timetable").update(update_data).eq("id", entry_id).execute()
    return result.data[0]


@router.delete("/{entry_id}")
async def delete_timetable(entry_id: str, current: dict = Depends(get_current_teacher)):
    """Delete a timetable entry."""
    supabase = get_supabase()
    existing = supabase.table("timetable").select("id").eq("id", entry_id).eq("teacher_id", current["teacher_id"]).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Timetable entry not found")
    supabase.table("timetable").delete().eq("id", entry_id).execute()
    return {"message": "Timetable entry deleted"}
