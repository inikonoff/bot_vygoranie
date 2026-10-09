-- Запустить один раз в Supabase SQL Editor.

-- 1. Хранилище FSM (состояния тестов/дневника переживают перезапуск)
create table if not exists fsm_states (
    key        text primary key,
    state      text,
    data       jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

-- 2. Согласие на еженедельный дайджест (по умолчанию выключено)
alter table users add column if not exists digest_enabled boolean not null default false;

-- 3. База знаний: полнотекстовый поиск вместо эмбеддингов
create table if not exists knowledge_base (
    id       bigserial primary key,
    content  text not null,
    metadata jsonb default '{}'::jsonb
);

do $$
begin
    -- если таблица создана раньше под вектора, колонка embedding не должна мешать вставке
    if exists (select 1 from information_schema.columns
               where table_name = 'knowledge_base' and column_name = 'embedding') then
        alter table knowledge_base alter column embedding drop not null;
    end if;
end $$;

alter table knowledge_base
    add column if not exists fts tsvector
    generated always as (to_tsvector('russian', content)) stored;

create index if not exists knowledge_base_fts_idx on knowledge_base using gin (fts);

create or replace function search_knowledge(query_text text, match_count int default 3)
returns table (content text, rank real)
language sql stable as $$
    with words as (
        select distinct w
        from regexp_split_to_table(
                 regexp_replace(lower(query_text), '[^[:alnum:]а-яё]+', ' ', 'g'), ' ') as w
        where char_length(w) >= 4
    ),
    q as (select to_tsquery('russian', string_agg(w, ' | ')) as tsq from words)
    select k.content, ts_rank(k.fts, q.tsq) as rank
    from knowledge_base k, q
    where q.tsq is not null and k.fts @@ q.tsq
    order by rank desc
    limit match_count;
$$;
