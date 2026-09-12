from pathlib import Path
import os
import re
from uuid import UUID

from pypdf import PdfReader

from app.db.supabase import supabase
from app.rag.embeddings import create_embedding


DATA_DIR = Path("data/hotel")
PDF_SOURCE = "lusso_knowledge_base.pdf"

CHUNK_SIZE = 1800
CHUNK_OVERLAP = 250


def clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            paragraph_break = text.rfind("\n\n", start, end)

            if paragraph_break > start + 500:
                end = paragraph_break

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = max(end - overlap, start + 1)

    return chunks


def extract_pdf_chunks(pdf_path: Path) -> list[dict]:
    reader = PdfReader(pdf_path)
    records = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = clean_text(page.extract_text() or "")

        if not page_text:
            print(f"Skipped empty page: {page_number}")
            continue

        page_chunks = split_text(page_text)

        for chunk_number, content in enumerate(page_chunks, start=1):
            records.append({
                "title": (
                    f"Lusso Knowledge Base - "
                    f"Page {page_number} - "
                    f"Chunk {chunk_number}"
                ),
                "content": content,
                "source": PDF_SOURCE,
            })

    return records


def ingest_lusso_pdf(hotel_id: UUID):
    pdf_path = DATA_DIR / PDF_SOURCE

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF not found at: {pdf_path.resolve()}"
        )

    records = extract_pdf_chunks(pdf_path)

    print(f"Prepared {len(records)} knowledge chunks.")

    # Removes an earlier ingestion of this same PDF.
    # This prevents duplicate chunks when the script is rerun.
    (
        supabase
        .table("documents")
        .delete()
        .eq("source", PDF_SOURCE)
        .eq("hotel_id", str(hotel_id))
        .execute()
    )

    for index, record in enumerate(records, start=1):
        embedding = create_embedding(record["content"])

        supabase.table("documents").insert({
            **record,
            "embedding": embedding,
            "hotel_id": str(hotel_id),
        }).execute()

        print(
            f"Ingested {index}/{len(records)}: "
            f"{record['title']}"
        )

    print("Lusso knowledge-base ingestion completed.")


if __name__ == "__main__":
    configured_hotel_id = os.getenv("HOTEL_ID")
    if not configured_hotel_id:
        raise ValueError("HOTEL_ID is required for tenant-safe ingestion")
    ingest_lusso_pdf(UUID(configured_hotel_id))
