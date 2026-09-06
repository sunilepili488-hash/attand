from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path
import sys

from auth.router import router as auth_router
from students.router import router as students_router
from timetable.router import router as timetable_router
from sessions.router import router as sessions_router
from scan.router import router as scan_router

app = FastAPI(title="AttendScan API", version="1.0.0", description="Student Attendance Scanner Backend")

# CORS - allow all origins (tighten in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all API routers
app.include_router(auth_router)
app.include_router(students_router)
app.include_router(timetable_router)
app.include_router(sessions_router)
app.include_router(scan_router)


@app.get("/health")
async def health():
    """Health check - verifies Supabase env vars are configured."""
    try:
        from config import settings
        url_preview = settings.SUPABASE_URL[:30] + "..." if settings.SUPABASE_URL else "NOT SET"
        supabase_ok = bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY)
        return {
            "status": "ok" if supabase_ok else "degraded",
            "supabase_configured": supabase_ok,
            "supabase_url_preview": url_preview,
        }
    except Exception as e:
        return JSONResponse(status_code=503, content={"status": "error", "detail": str(e)})


# Serve built frontend static files in production
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(status_code=404, content={"detail": "Frontend not built. Run: cd frontend && npm run build"})
