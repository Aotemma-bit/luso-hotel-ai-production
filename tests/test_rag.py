from types import SimpleNamespace
from uuid import UUID

from app.rag import retrieval

HOTEL_A = UUID("11111111-1111-1111-1111-111111111111")


class Rpc:
    def execute(self):
        return SimpleNamespace(data=[{"content": "Check-in is at 2 PM."}])


class Supabase:
    def __init__(self): self.params = None
    def rpc(self, name, params):
        assert name == "match_hotel_documents"
        self.params = params
        return Rpc()


def test_retrieval_sends_authenticated_hotel_to_rpc(monkeypatch):
    fake = Supabase()
    monkeypatch.setattr(retrieval, "supabase", fake)
    monkeypatch.setattr(retrieval, "create_embedding", lambda _: [0.1, 0.2])
    results = retrieval.search_documents("What time is check-in?", HOTEL_A)
    assert results[0]["content"] == "Check-in is at 2 PM."
    assert fake.params["requested_hotel_id"] == str(HOTEL_A)
