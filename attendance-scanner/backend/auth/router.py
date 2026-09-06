from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from supabase import create_client, Client
from config import settings
from auth.utils import hash_password, verify_password, create_access_token, get_current_teacher

router = APIRouter(prefix="/auth", tags=["auth"])


def get_supabase() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    college_name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(data: RegisterRequest):
    """Register a new teacher account."""
    supabase = get_supabase()

    # Check if email already exists
    existing = supabase.table("teachers").select("id").eq("email", data.email).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Hash password and insert teacher
    password_hash = hash_password(data.password)
    result = supabase.table("teachers").insert({
        "name": data.name,
        "email": data.email,
        "password_hash": password_hash,
        "college_name": data.college_name,
    }).execute()

    teacher = result.data[0]
    token = create_access_token({"sub": teacher["id"], "email": teacher["email"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "teacher": {
            "id": teacher["id"],
            "name": teacher["name"],
            "email": teacher["email"],
            "college_name": teacher.get("college_name", ""),
        }
    }


@router.post("/login")
async def login(data: LoginRequest):
    """Login with email and password, returns JWT."""
    supabase = get_supabase()

    result = supabase.table("teachers").select("*").eq("email", data.email).execute()
    if not result.data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    teacher = result.data[0]
    if not verify_password(data.password, teacher["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": teacher["id"], "email": teacher["email"]})

    return {
        "access_token": token,
        "token_type": "bearer",
        "teacher": {
            "id": teacher["id"],
            "name": teacher["name"],
            "email": teacher["email"],
            "college_name": teacher.get("college_name", ""),
        }
    }


@router.get("/me")
async def get_me(current: dict = Depends(get_current_teacher)):
    """Get current teacher profile."""
    supabase = get_supabase()
    result = supabase.table("teachers").select("id,name,email,college_name,created_at").eq("id", current["teacher_id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return result.data[0]
