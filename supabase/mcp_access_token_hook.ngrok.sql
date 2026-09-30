-- Installation TEMPLATE, not an automatic migration. No RLS policies are changed.
-- Prepared for the current ngrok MCP origin; review before installation.
-- If a Custom Access Token hook already exists, merge this logic into it instead.
-- Enable this function in Authentication > Hooks after reviewed installation.
begin;

create function public.courses_mcp_access_token_hook(event jsonb)
returns jsonb
language plpgsql
stable
security invoker
set search_path = ''
as $$
declare
  claims jsonb := event -> 'claims';
  resource text := 'https://minerva-unweakening-meteorically.ngrok-free.dev/mcp';
begin
  -- Supabase supplies client_id only for OAuth tokens, including refreshes.
  -- Keep ordinary website and anonymous tokens at their original audience.
  if claims ->> 'role' = 'authenticated'
     and claims -> 'is_anonymous' = 'false'::jsonb
     and jsonb_typeof(claims -> 'client_id') = 'string'
     and btrim(claims ->> 'client_id') <> ''
     and claims ->> 'client_id' = btrim(claims ->> 'client_id') then
    claims := jsonb_set(
      claims,
      '{aud}',
      jsonb_build_array('authenticated', resource)
    );
  end if;

  -- Preserve role, sub, is_anonymous, session_id, and every other original claim.
  return jsonb_build_object('claims', claims);
end;
$$;

-- Abort the entire transaction if the template has not been configured.
do $$
begin
  if position('REPLACE_' in pg_get_functiondef(
      'public.courses_mcp_access_token_hook(jsonb)'::regprocedure)) > 0 then
    raise exception 'Configure the MCP resource before installing this hook';
  end if;
end;
$$;

grant usage on schema public to supabase_auth_admin;
revoke all on function public.courses_mcp_access_token_hook(jsonb)
  from public, anon, authenticated;
grant execute on function public.courses_mcp_access_token_hook(jsonb)
  to supabase_auth_admin;

commit;
