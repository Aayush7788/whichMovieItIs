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
create_movie_search_documents_table_sql = """
    create table if not exists movie_search_documents (
        id bigserial primary key,
        movie_id bigint not null references movies(id) on delete cascade,
        wikipedia_movie_id text not null,
        title text not null,
        document_type text not null,
        source text not null,
        source_document_id text not null,
        content text not null,
        metadata jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    );
"""

add_movie_search_documents_vector_sql = """
    alter table movie_search_documents
    add column if not exists search_vector tsvector
    generated always as (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(document_type, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(content, '')), 'C')
    ) stored;
"""

create_movie_search_documents_unique_index_sql = """
    create unique index if not exists movie_search_documents_source_uidx
    on movie_search_documents (source, document_type, source_document_id);
"""

create_movie_search_documents_movie_index_sql = """
    create index if not exists movie_search_documents_movie_idx
    on movie_search_documents (movie_id, document_type);
"""

create_movie_search_documents_vector_index_sql = """
    create index if not exists movie_search_documents_vector_idx
    on movie_search_documents using gin (search_vector);
"""

create_movie_search_document_embeddings_table_sql = """
    create table if not exists movie_search_document_embeddings (
        document_id bigint primary key
            references movie_search_documents(id) on delete cascade,
        embedding vector(384) not null,
        embedding_model text not null,
        updated_at timestamptz not null default now()
    );
"""

create_movie_search_document_embeddings_index_sql = """
    create index if not exists movie_search_document_embeddings_hnsw_idx
    on movie_search_document_embeddings
    using hnsw (embedding vector_cosine_ops);
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
            cur.execute(create_movie_search_documents_table_sql)
            cur.execute(add_movie_search_documents_vector_sql)
            cur.execute(create_movie_search_documents_unique_index_sql)
            cur.execute(create_movie_search_documents_movie_index_sql)
            cur.execute(create_movie_search_documents_vector_index_sql)
            cur.execute(create_movie_search_document_embeddings_table_sql)
            cur.execute(create_movie_search_document_embeddings_index_sql)
            
        conn.commit()

    print("movies table ready")

if __name__ == "__main__":
    main()
