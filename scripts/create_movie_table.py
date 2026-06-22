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

add_search_embedding_column_sql = """
    alter table movies
    add column if not exists search_embedding vector(384);
"""

add_embedding_model_column_sql = """
    alter table movies
    add column if not exists embedding_model text;
"""

create_search_embedding_index_sql = """
    create index if not exists movies_search_embedding_hnsw_idx
    on movies using hnsw (search_embedding vector_cosine_ops);
"""
add_tmdb_metadata_columns_sql = """
    alter table movies
    add column if not exists tmdb_id bigint,
    add column if not exists poster_path text,
    add column if not exists metadata_source text,
    add column if not exists metadata_match_status text,
    add column if not exists metadata_updated_at timestamptz;
"""

create_tmdb_id_index_sql = """
    create index if not exists movies_tmdb_id_idx
    on movies (tmdb_id)
    where tmdb_id is not null;
"""

def main()-> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(create_vector_extension_sql)
            cur.execute(create_movie_table_sql) 
            cur.execute(add_search_vector_column_sql)
            cur.execute(create_search_vector_index_sql)
            cur.execute(add_search_embedding_column_sql)
            cur.execute(add_embedding_model_column_sql)
            cur.execute(create_search_embedding_index_sql)
            cur.execute(add_tmdb_metadata_columns_sql)
            cur.execute(create_tmdb_id_index_sql)
            
        conn.commit()

    print("movies table ready")

if __name__ == "__main__":
    main()
