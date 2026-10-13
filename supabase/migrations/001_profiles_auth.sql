-- Nexus Supabase auth/profile setup
-- Run this migration in the Nexus Supabase SQL Editor.

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  username text not null unique,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint profiles_username_format check (username ~ '^[a-zA-Z0-9_]{3,30}$')
);

alter table public.profiles enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
  on public.profiles for select
  to authenticated
  using (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own"
  on public.profiles for update
  to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  requested_username text;
  base_username text;
  candidate text;
  n integer := 0;
begin
  requested_username := lower(trim(coalesce(new.raw_user_meta_data->>'username', '')));
  if requested_username !~ '^[a-z0-9_]{3,30}$' then
    base_username := lower(regexp_replace(split_part(coalesce(new.email, 'user'), '@', 1), '[^a-z0-9_]', '', 'g'));
    base_username := left(base_username, 24);
    if length(base_username) < 3 then base_username := 'user'; end if;
    candidate := base_username;
    while exists (select 1 from public.profiles where username = candidate) loop
      n := n + 1;
      candidate := left(base_username, 24) || n::text;
    end loop;
    requested_username := candidate;
  end if;

  insert into public.profiles (id, username, display_name)
  values (
    new.id,
    requested_username,
    nullif(trim(coalesce(new.raw_user_meta_data->>'full_name', '')), '')
  )
  on conflict (id) do nothing;

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_updated_at on public.profiles;
create trigger profiles_updated_at
  before update on public.profiles
  for each row execute procedure public.set_updated_at();
