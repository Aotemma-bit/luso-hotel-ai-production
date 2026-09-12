-- Run this once in the Supabase SQL Editor.
-- It performs vector search only inside the authenticated hotel's documents.
create or replace function public.match_hotel_documents(
    query_embedding vector,
    requested_hotel_id uuid,
    match_count integer default 5
)
returns table (
    id bigint,
    title text,
    content text,
    source text,
    metadata jsonb,
    similarity double precision
)
language sql
stable
set search_path = ''
as $$
    select
        documents.id,
        documents.title,
        documents.content,
        documents.source,
        documents.metadata,
        1 - (documents.embedding <=> query_embedding) as similarity
    from public.documents as documents
    where documents.hotel_id = requested_hotel_id
    order by documents.embedding <=> query_embedding
    limit greatest(1, least(match_count, 20));
$$;

revoke all on function public.match_hotel_documents(vector, uuid, integer) from public;
grant execute on function public.match_hotel_documents(vector, uuid, integer) to service_role;
