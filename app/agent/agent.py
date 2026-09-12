from openai import OpenAI
from uuid import UUID

from app.agent.prompts import SYSTEM_PROMPT
from app.core.config import OPENAI_API_KEY, OPENAI_MODEL
from app.rag.retrieval import search_documents


client = OpenAI(api_key=OPENAI_API_KEY)


def ask_ai(message: str, hotel_id: UUID) -> str:
    documents = search_documents(message, hotel_id)

    if documents:
        context = "\n\n".join(
            [
                (
                    f"SOURCE: {document['source']}\n"
                    f"TITLE: {document['title']}\n"
                    f"{document['content']}"
                )
                for document in documents
            ]
        )
    else:
        context = "No relevant Lusso Hotel information was retrieved."

    prompt = f"""
{SYSTEM_PROMPT}

LUSSO HOTEL KNOWLEDGE CONTEXT:

{context}

GUEST MESSAGE:

{message}

Answer using only the supplied Lusso Hotel knowledge for
hotel-specific facts.
"""

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
    )

    return response.output_text
    
