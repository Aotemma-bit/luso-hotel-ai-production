-- Luso Hotel AI production migration. Safe to rerun.
-- Run with the Supabase SQL Editor before starting version 2.0.

create index if not exists guests_hotel_created_idx
    on public.guests (hotel_id, created_at desc);
create index if not exists guest_requests_hotel_created_idx
    on public.guest_requests (hotel_id, created_at desc);
create index if not exists guest_requests_hotel_status_idx
    on public.guest_requests (hotel_id, status);
create index if not exists documents_hotel_source_idx
    on public.documents (hotel_id, source);
create index if not exists hotel_users_user_hotel_idx
    on public.hotel_users (user_id, hotel_id);
create unique index if not exists hotel_users_user_hotel_unique
    on public.hotel_users (user_id, hotel_id);

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
        1 - (documents.embedding OPERATOR(extensions.<=>) query_embedding) as similarity
    from public.documents as documents
    where documents.hotel_id = requested_hotel_id
    order by documents.embedding OPERATOR(extensions.<=>) query_embedding
    limit greatest(1, least(match_count, 20));
$$;

create or replace function public.hotel_dashboard_metrics(requested_hotel_id uuid)
returns jsonb
language sql
stable
set search_path = ''
as $$
    select jsonb_build_object(
        'total_guests', (
            select count(*) from public.guests g
            where g.hotel_id = requested_hotel_id
        ),
        'total_requests', (
            select count(*) from public.guest_requests r
            where r.hotel_id = requested_hotel_id
        ),
        'open_requests', (
            select count(*) from public.guest_requests r
            where r.hotel_id = requested_hotel_id
              and lower(coalesce(r.status, 'open')) not in ('completed', 'closed', 'resolved')
        ),
        'high_priority', (
            select count(*) from public.guest_requests r
            where r.hotel_id = requested_hotel_id
              and lower(coalesce(r.status, 'open')) not in ('completed', 'closed', 'resolved')
              and lower(coalesce(r.priority, 'normal')) in ('high', 'urgent', 'critical')
        ),
        'active_departments', (
            select count(distinct r.assigned_department) from public.guest_requests r
            where r.hotel_id = requested_hotel_id
              and r.assigned_department is not null
              and lower(coalesce(r.status, 'open')) not in ('completed', 'closed', 'resolved')
        ),
        'knowledge_documents', (
            select count(*) from public.documents d
            where d.hotel_id = requested_hotel_id
        ),
        'departments', coalesce((
            select jsonb_object_agg(grouped.name, grouped.amount)
            from (
                select coalesce(r.assigned_department, 'Unassigned') as name, count(*) as amount
                from public.guest_requests r
                where r.hotel_id = requested_hotel_id
                group by coalesce(r.assigned_department, 'Unassigned')
            ) grouped
        ), '{}'::jsonb),
        'priorities', coalesce((
            select jsonb_object_agg(grouped.name, grouped.amount)
            from (
                select lower(coalesce(r.priority, 'normal')) as name, count(*) as amount
                from public.guest_requests r
                where r.hotel_id = requested_hotel_id
                group by lower(coalesce(r.priority, 'normal'))
            ) grouped
        ), '{}'::jsonb),
        'statuses', coalesce((
            select jsonb_object_agg(grouped.name, grouped.amount)
            from (
                select lower(coalesce(r.status, 'open')) as name, count(*) as amount
                from public.guest_requests r
                where r.hotel_id = requested_hotel_id
                group by lower(coalesce(r.status, 'open'))
            ) grouped
        ), '{}'::jsonb),
        'sources', coalesce((
            select jsonb_agg(jsonb_build_object('name', grouped.name, 'chunks', grouped.amount) order by grouped.name)
            from (
                select coalesce(d.source, 'Unknown') as name, count(*) as amount
                from public.documents d
                where d.hotel_id = requested_hotel_id
                group by coalesce(d.source, 'Unknown')
            ) grouped
        ), '[]'::jsonb)
    );
$$;

revoke all on function public.match_hotel_documents(vector, uuid, integer) from public;
revoke all on function public.hotel_dashboard_metrics(uuid) from public;
grant execute on function public.match_hotel_documents(vector, uuid, integer) to service_role;
grant execute on function public.hotel_dashboard_metrics(uuid) to service_role;

