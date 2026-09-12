from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.audit import record_audit
from app.core.config import settings
from app.core.security import UserContext, get_current_user, require_roles
from app.db.supabase import supabase

router = APIRouter(tags=["Guests"])


class GuestCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = None
    room_number: str | None = Field(default=None, max_length=30)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("name cannot be blank")
        return value


@router.get("/guests")
def list_guests(
    context: UserContext = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=settings.max_page_size),
    offset: int = Query(default=0, ge=0),
):
    result = (
        supabase.table("guests")
        .select("id,name,phone,email,room_number,created_at", count="exact")
        .eq("hotel_id", str(context.hotel_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return {"count": result.count or 0, "items": result.data or [], "limit": limit, "offset": offset}


@router.post("/guests", status_code=201)
def create_guest(
    guest: GuestCreate,
    context: UserContext = Depends(require_roles("owner", "admin", "manager", "front_desk")),
):
    payload = guest.model_dump(mode="json")
    payload["hotel_id"] = str(context.hotel_id)
    try:
        result = supabase.table("guests").insert(payload).execute()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to create guest") from error
    created = (result.data or [{}])[0]
    record_audit(context, "guest.created", "guest", created.get("id"))
    return created
