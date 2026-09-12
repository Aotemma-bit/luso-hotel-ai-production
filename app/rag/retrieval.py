import math
from uuid import UUID

from app.db.supabase import supabase
from app.rag.embeddings import create_embedding


def _parse_vector(value: object) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if isinstance(value, str):
        text = value.strip().strip("[]")
        return [float(item) for item in text.split(",") if item.strip()]
    return []


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return -1.0
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if not left_norm or not right_norm:
        return -1.0
    return dot_product / (left_norm * right_norm)


def search_documents(
    query: str,
    hotel_id: UUID,
    match_count: int = 5,
) -> list[dict]:
    query = query.strip()
    if not query:
        return []

    safe_match_count = max(1, min(match_count, 20))
    query_embedding = create_embedding(query)

    try:
        result = supabase.rpc(
            "match_hotel_documents",
            {
                "query_embedding": query_embedding,
                "requested_hotel_id": str(hotel_id),
                "match_count": safe_match_count,
            },
        ).execute()
        return result.data or []
    except Exception:
        # Safe compatibility fallback until the tenant-aware RPC migration
        # has been installed. It still filters by hotel before ranking.
        result = (
            supabase.table("documents")
            .select("id, title, content, source, metadata, embedding")
            .eq("hotel_id", str(hotel_id))
            .execute()
        )
        ranked = []
        for document in result.data or []:
            similarity = _cosine_similarity(
                query_embedding,
                _parse_vector(document.pop("embedding", None)),
            )
            document["similarity"] = similarity
            ranked.append(document)
        ranked.sort(key=lambda item: item["similarity"], reverse=True)
        return ranked[:safe_match_count]
