from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.audit import record_audit
from app.core.config import settings
from app.core.security import UserContext, get_current_user, require_roles
from app.db.supabase import supabase

router = APIRouter(tags=["Requests"])


class RequestCreate(BaseModel):
    guest_id: int
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    priority: Literal["normal", "high", "urgent", "critical"] = "normal"
    assigned_department: str | None = Field(default=None, max_length=80)


class RequestUpdate(BaseModel):
    status: Literal["open", "in_progress", "completed", "resolved", "closed"] | None = None
    priority: Literal["normal", "high", "urgent", "critical"] | None = None
    assigned_department: str | None = Field(default=None, max_length=80)


@router.get("/requests")
def get_requests(
    context: UserContext = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
):
    result = (
        supabase.table("guest_requests")
        .select("*", count="exact")
        .eq("hotel_id", str(context.hotel_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"count": result.count or 0, "items": result.data or [], "limit": limit, "offset": offset}


@router.post("/requests", status_code=201)
def create_request(
    request: RequestCreate,
    context: UserContext = Depends(require_roles("owner", "admin", "manager", "front_desk", "staff")),
):
    guest = (
        supabase.table("guests").select("id").eq("id", request.guest_id)
        .eq("hotel_id", str(context.hotel_id)).limit(1).execute()
    )
    if not guest.data:
        raise HTTPException(status_code=404, detail="Guest not found")
    payload = request.model_dump()
    payload["hotel_id"] = str(context.hotel_id)
    result = supabase.table("guest_requests").insert(payload).execute()
    created = (result.data or [{}])[0]
    record_audit(context, "request.created", "guest_request", created.get("id"))
    return created


@router.patch("/requests/{request_id}")
def update_request(
    request_id: int,
    update: RequestUpdate,
    context: UserContext = Depends(require_roles("owner", "admin", "manager", "front_desk", "staff")),
):
    payload = update.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=422, detail="Provide at least one field to update")
    result = (
        supabase.table("guest_requests").update(payload).eq("id", request_id)
        .eq("hotel_id", str(context.hotel_id)).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Request not found")
    record_audit(context, "request.updated", "guest_request", request_id, {"fields": sorted(payload)})
    return result.data[0]
