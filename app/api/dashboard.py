from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.config import settings
from app.core.security import UserContext, get_current_user
from app.db.supabase import supabase

router = APIRouter(tags=["Dashboard"])


def fetch_hotel_name(hotel_id: UUID) -> str:
    try:
        result = supabase.table("hotels").select("name").eq("id", str(hotel_id)).limit(1).execute()
        return (result.data or [{}])[0].get("name") or "Hotel"
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to load hotel information") from error


def fetch_metrics(hotel_id: UUID) -> dict:
    try:
        result = supabase.rpc("hotel_dashboard_metrics", {"requested_hotel_id": str(hotel_id)}).execute()
        if isinstance(result.data, dict):
            return result.data
        if isinstance(result.data, list) and result.data:
            return result.data[0]
        return {}
    except Exception as error:
        raise HTTPException(status_code=503, detail="Dashboard metrics migration is required") from error


@router.get("/me")
def current_account(context: UserContext = Depends(get_current_user)):
    return {
        "user_id": context.user_id,
        "email": getattr(context.user, "email", None),
        "hotel_id": str(context.hotel_id),
        "hotel": fetch_hotel_name(context.hotel_id),
        "role": context.role,
    }


@router.get("/dashboard/summary")
def dashboard_summary(context: UserContext = Depends(get_current_user)):
    metrics = fetch_metrics(context.hotel_id)
    return {
        "hotel": fetch_hotel_name(context.hotel_id),
        "total_guests": metrics.get("total_guests", 0),
        "open_requests": metrics.get("open_requests", 0),
        "high_priority": metrics.get("high_priority", 0),
        "active_departments": metrics.get("active_departments", 0),
        "knowledge_documents": metrics.get("knowledge_documents", 0),
    }


@router.get("/dashboard/guests")
def dashboard_guests(
    context: UserContext = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
):
    try:
        result = (
            supabase.table("guests")
            .select("id,name,phone,email,room_number,created_at", count="exact")
            .eq("hotel_id", str(context.hotel_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to load guests") from error
    return {"count": result.count or 0, "items": result.data or [], "limit": limit, "offset": offset}


@router.get("/dashboard/requests")
def dashboard_requests(
    context: UserContext = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
):
    try:
        result = (
            supabase.table("guest_requests").select("*", count="exact")
            .eq("hotel_id", str(context.hotel_id)).order("created_at", desc=True)
            .range(offset, offset + limit - 1).execute()
        )
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to load requests") from error
    return {"count": result.count or 0, "items": result.data or [], "limit": limit, "offset": offset}


@router.get("/dashboard/knowledge")
def dashboard_knowledge(context: UserContext = Depends(get_current_user)):
    metrics = fetch_metrics(context.hotel_id)
    return {"chunks": metrics.get("knowledge_documents", 0), "sources": metrics.get("sources", [])}


@router.get("/dashboard/analytics")
def dashboard_analytics(context: UserContext = Depends(get_current_user)):
    metrics = fetch_metrics(context.hotel_id)
    return {
        "total_requests": metrics.get("total_requests", 0),
        "departments": metrics.get("departments", {}),
        "priorities": metrics.get("priorities", {}),
        "statuses": metrics.get("statuses", {}),
    }
