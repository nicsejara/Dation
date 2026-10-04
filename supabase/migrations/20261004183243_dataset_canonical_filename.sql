-- Canonical filenames for Dation-managed dataset versions.
-- User-provided source filenames remain preserved in original_filename.
begin;

alter table public.datasets
  add column if not exists canonical_filename text;

comment on column public.datasets.canonical_filename is
  'Dation-controlled filename for operational display and Storage naming. The user-provided source name remains in original_filename.';

notify pgrst, 'reload schema';

commit;
