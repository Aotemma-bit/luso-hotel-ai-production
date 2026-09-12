"""Live destructive-safe tenant test.

Creates one temporary guest in Hotel A, verifies Hotel B cannot see it, then
removes the temporary record with the server-side Supabase credential.
"""
import os
import sys
from uuid import uuid4

import httpx
from supabase import create_client


def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def login(url: str, publishable_key: str, email: str, password: str) -> str:
    client = create_client(url, publishable_key)
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    if not response.session:
        raise RuntimeError(f"Login failed for {email}")
    return response.session.access_token


def main() -> int:
    api_url = required("TEST_API_URL").rstrip("/")
    supabase_url = required("SUPABASE_URL")
    publishable_key = required("SUPABASE_PUBLISHABLE_KEY")
    server_key = required("SUPABASE_KEY")
    token_a = login(supabase_url, publishable_key, required("HOTEL_A_EMAIL"), required("HOTEL_A_PASSWORD"))
    token_b = login(supabase_url, publishable_key, required("HOTEL_B_EMAIL"), required("HOTEL_B_PASSWORD"))
    marker = f"TENANT-ISOLATION-{uuid4()}"
    guest_id = None
    hotel_a_id = None
    admin = create_client(supabase_url, server_key)
    with httpx.Client(base_url=api_url, timeout=30) as client:
        me_a = client.get("/api/me", headers={"Authorization": f"Bearer {token_a}"})
        me_b = client.get("/api/me", headers={"Authorization": f"Bearer {token_b}"})
        me_a.raise_for_status()
        me_b.raise_for_status()
        hotel_a_id = me_a.json()["hotel_id"]
        hotel_b_id = me_b.json()["hotel_id"]
        if hotel_a_id == hotel_b_id:
            raise RuntimeError("The two test users must belong to different hotels")
        try:
            created = client.post(
                "/api/guests",
                headers={"Authorization": f"Bearer {token_a}"},
                json={"name": marker, "room_number": "TEST"},
            )
            created.raise_for_status()
            guest_id = created.json()["id"]
            visible_to_a = client.get("/api/dashboard/guests?limit=200", headers={"Authorization": f"Bearer {token_a}"})
            visible_to_b = client.get("/api/dashboard/guests?limit=200", headers={"Authorization": f"Bearer {token_b}"})
            visible_to_a.raise_for_status()
            visible_to_b.raise_for_status()
            assert any(row.get("name") == marker for row in visible_to_a.json()["items"]), "Hotel A cannot see its test guest"
            assert not any(row.get("name") == marker for row in visible_to_b.json()["items"]), "TENANT LEAK: Hotel B saw Hotel A data"
            forced = client.get(
                "/api/dashboard/summary",
                headers={"Authorization": f"Bearer {token_a}", "X-Hotel-ID": hotel_b_id},
            )
            assert forced.status_code == 403, f"Expected cross-hotel selection to return 403, received {forced.status_code}"
            print("LIVE TENANT ISOLATION: PASSED")
            return 0
        finally:
            if guest_id is not None and hotel_a_id is not None:
                admin.table("guests").delete().eq("id", guest_id).eq("hotel_id", hotel_a_id).execute()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"LIVE TENANT ISOLATION: FAILED - {error}", file=sys.stderr)
        raise SystemExit(1)
