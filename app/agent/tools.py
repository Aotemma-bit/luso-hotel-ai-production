from app.db.supabase import supabase
from uuid import UUID


def create_guest_request(
    guest_id: int,
    category: str,
    description: str,
    hotel_id: UUID,
    priority: str = "normal",
    department: str = "Front Desk"
) -> list[dict]:
    guest_result = (
        supabase.table("guests")
        .select("id")
        .eq("id", guest_id)
        .eq("hotel_id", str(hotel_id))
        .limit(1)
        .execute()
    )
    if not guest_result.data:
        raise ValueError("Guest does not belong to the authenticated hotel")

    result = (
        supabase.table("guest_requests")
        .insert({
            "guest_id": guest_id,
            "hotel_id": str(hotel_id),
            "category": category,
            "description": description,
            "priority": priority,
            "assigned_department": department,
            "status": "open"
        })
        .execute()
    )

    return result.data or []
