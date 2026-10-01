-- Dataset library support for Dispatch v1.
-- Apply manually in Supabase SQL Editor after reviewing the existing Dispatch migration.
begin;

alter table public.datasets
    add column if not exists archived_at timestamptz,
    add column if not exists is_sample boolean not null default false;

create index if not exists datasets_dispatch_active_idx
    on public.datasets(dataset_type, created_at desc)
    where archived_at is null
      and dataset_type in ('orders', 'fleet');

notify pgrst, 'reload schema';

commit;

-- Non-destructive rollback guidance:
-- 1. Deploy the previous application.
-- 2. Keep archived_at and is_sample while any new application data may reference them.
-- 3. Only after confirming there are no dependencies, the owner may drop the index/columns manually.
