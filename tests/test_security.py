from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.core import security

HOTEL_A = "11111111-1111-1111-1111-111111111111"
HOTEL_B = "22222222-2222-2222-2222-222222222222"


class Query:
    def __init__(self, rows): self.rows = rows
    def select(self, *_args, **_kwargs): return self
    def eq(self, field, value):
        self.rows = [row for row in self.rows if str(row.get(field)) == str(value)]
        return self
    def limit(self, _value): return self
    def execute(self): return SimpleNamespace(data=self.rows)


class Supabase:
    def __init__(self):
        self.auth = SimpleNamespace(get_user=lambda _token: SimpleNamespace(user=SimpleNamespace(id="user-a", email="a@example.com")))
    def table(self, name):
        assert name == "hotel_users"
        return Query([{"user_id": "user-a", "hotel_id": HOTEL_A, "role": "manager"}])


def test_user_context_is_derived_from_server_membership(monkeypatch):
    monkeypatch.setattr(security, "supabase", Supabase())
    context = security.get_current_user("Bearer valid-token", None)
    assert context.hotel_id == UUID(HOTEL_A)
    assert context.role == "manager"


def test_user_cannot_select_another_hotel(monkeypatch):
    monkeypatch.setattr(security, "supabase", Supabase())
    with pytest.raises(HTTPException) as caught:
        security.get_current_user("Bearer valid-token", HOTEL_B)
    assert caught.value.status_code == 403


def test_role_dependency_rejects_unauthorised_role():
    dependency = security.require_roles("owner", "admin")
    context = security.UserContext(SimpleNamespace(id="user-a"), UUID(HOTEL_A), "staff")
    with pytest.raises(HTTPException) as caught:
        dependency(context)
    assert caught.value.status_code == 403
