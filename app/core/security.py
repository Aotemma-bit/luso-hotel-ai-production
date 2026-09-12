from dataclasses import dataclass
from typing import Any, Callable
from uuid import UUID

from fastapi import Depends, Header, HTTPException

from app.db.supabase import supabase

ROLE_ALIASES = {"administrator": "admin", "frontdesk": "front_desk", "front desk": "front_desk"}
KNOWN_ROLES = {"owner", "admin", "manager", "front_desk", "staff"}


@dataclass(frozen=True)
class UserContext:
    user: Any
    hotel_id: UUID
    role: str

    @property
    def user_id(self) -> str:
        return str(self.user.id)


def _normalise_role(value: object) -> str:
    role = str(value or "staff").strip().lower()
    return ROLE_ALIASES.get(role, role)


def get_current_user(
    authorization: str | None = Header(default=None),
    x_hotel_id: str | None = Header(default=None),
) -> UserContext:
    if not authorization:
        raise HTTPException(status_code=401, detail="Authentication required")
    scheme, _, token = authorization.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="Invalid authorization header")
    try:
        response = supabase.auth.get_user(token)
        user = response.user
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid or expired session") from error
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    try:
        query = supabase.table("hotel_users").select("hotel_id, role").eq("user_id", str(user.id))
        if x_hotel_id:
            try:
                selected_hotel = str(UUID(x_hotel_id))
            except ValueError as error:
                raise HTTPException(status_code=400, detail="X-Hotel-ID must be a valid UUID") from error
            query = query.eq("hotel_id", selected_hotel)
        membership_result = query.limit(20).execute()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=503, detail="Unable to verify hotel membership") from error
    memberships = membership_result.data or []
    if not memberships:
        raise HTTPException(status_code=403, detail="This account is not assigned to the selected hotel")
    if len(memberships) > 1 and not x_hotel_id:
        raise HTTPException(status_code=409, detail="Select a hotel using the X-Hotel-ID header")
    membership = memberships[0]
    try:
        hotel_id = UUID(str(membership["hotel_id"]))
    except (KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=403, detail="This account has an invalid hotel assignment") from error
    role = _normalise_role(membership.get("role"))
    if role not in KNOWN_ROLES:
        raise HTTPException(status_code=403, detail="This account has an unsupported role")
    return UserContext(user=user, hotel_id=hotel_id, role=role)


def require_roles(*roles: str) -> Callable[..., UserContext]:
    allowed = {_normalise_role(role) for role in roles}

    def authorised(context: UserContext = Depends(get_current_user)) -> UserContext:
        if context.role not in allowed:
            raise HTTPException(status_code=403, detail="Your role does not permit this action")
        return context

    return authorised
