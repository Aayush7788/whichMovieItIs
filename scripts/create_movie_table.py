import sys
from pathlib import Path

from backend.app.db import get_connection

create_vector_extension_sql = "create extension if not exists vector;"

create_movie_table_sql = """
create table if not exists movies (
    id bigserial primary key, 
    wikipedia_movie_id text unique not null, 
    freebase_movie_id text, 
    title text not null,
    release_date text, 
    box_office_revenue double precision, 
    runtime double precision, 
    languages jsonb not null default '[]'::jsonb, 
    countries jsonb not null default '[]'::jsonb, 
    genres jsonb not null default '[]'::jsonb, 
    plot_summary text not null, 
    source text not null, 
    created_at timestamptz not null default now()
);
"""

add_search_vector_column_sql = """
    alter table movies
    add column if not exists search_vector tsvector
    generated always as (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(plot_summary, '')), 'B')
    ) stored;
"""

create_search_vector_index_sql = """
    create index  if not exists movies_search_vector_idx
    on movies using gin (search_vector);
"""

def main()-> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_vector_extension_sql)
            cur.execute(create_movie_table_sql) 
            cur.execute(add_search_vector_column_sql)
            cur.execute(create_search_vector_index_sql)
        conn.commit()

    print("movies table ready")

if __name__ == "__main__":
    main()
