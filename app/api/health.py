from fastapi import APIRouter, HTTPException

from app.db.supabase import supabase

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/health/live")
def liveness():
    return {"status": "healthy", "service": "luso-hotel-ai", "version": "2.0.0"}


@router.get("/health/ready")
def readiness():
    try:
        supabase.table("hotels").select("id").limit(1).execute()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Database dependency unavailable") from error
    return {"status": "ready", "database": "connected"}
