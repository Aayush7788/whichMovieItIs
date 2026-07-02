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

add_movie_identity_columns_sql = """
    alter table movies
    add column if not exists movie_key text,
    add column if not exists search_boost_text text not null default '';

    update movies
    set movie_key = case
        when wikipedia_movie_id is not null
            then 'cmu:' || wikipedia_movie_id
        when tmdb_id is not null
            then 'tmdb:' || tmdb_id::text
        else 'legacy:' || id::text
    end
    where movie_key is null;

    alter table movies
    alter column wikipedia_movie_id drop not null;

    alter table movies
    alter column movie_key set not null;
"""

create_movie_key_index_sql = """
    create unique index if not exists movies_movie_key_uidx
    on movies (movie_key);
"""

add_movie_search_boost_vector_sql = """
    alter table movies
    add column if not exists search_boost_vector tsvector
    generated always as (
        setweight(
            to_tsvector('english', coalesce(search_boost_text, '')),
            'C'
        )
    ) stored;
"""

create_movie_search_boost_vector_index_sql = """
    create index if not exists movies_search_boost_vector_idx
    on movies using gin (search_boost_vector);
"""

create_movie_external_ids_table_sql = """
    create table if not exists movie_external_ids (
        id bigserial primary key,
        movie_id bigint not null references movies(id) on delete cascade,
        source text not null,
        external_id text not null,
        metadata jsonb not null default '{}'::jsonb,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        unique (source, external_id)
    );
"""

create_movie_external_ids_movie_index_sql = """
    create index if not exists movie_external_ids_movie_idx
    on movie_external_ids (movie_id, source);
"""

backfill_cmu_external_ids_sql = """
    insert into movie_external_ids (
        movie_id,
        source,
        external_id,
        updated_at
    )
    select
        id,
        'cmu_wikipedia_movie_id',
        wikipedia_movie_id,
        now()
    from movies
    where wikipedia_movie_id is not null
    on conflict (source, external_id)
    do update set
        movie_id = excluded.movie_id,
        updated_at = now();
"""

backfill_tmdb_external_ids_sql = """
    with ranked_tmdb_movies as (
        select
            id,
            tmdb_id::text as external_id,
            row_number() over (
                partition by tmdb_id
                order by
                    case
                        when metadata_match_status = 'matched'
                        then 0
                        else 1
                    end,
                    case
                        when poster_path is not null
                        then 0
                        else 1
                    end,
                    id
            ) as match_rank
        from movies
        where tmdb_id is not null
    )
    insert into movie_external_ids (
        movie_id,
        source,
        external_id,
        updated_at
    )
    select
        id,
        'tmdb',
        external_id,
        now()
    from ranked_tmdb_movies
    where match_rank = 1
    on conflict (source, external_id)
    do update set
        movie_id = excluded.movie_id,
        updated_at = now();
"""

add_movie_search_documents_identity_sql = """
    alter table movie_search_documents
    add column if not exists movie_key text;

    update movie_search_documents document
    set movie_key = movie.movie_key
    from movies movie
    where document.movie_id = movie.id
        and document.movie_key is null;

    alter table movie_search_documents
    alter column wikipedia_movie_id drop not null;

    alter table movie_search_documents
    alter column movie_key set not null;
"""

create_movie_search_documents_key_index_sql = """
    create index if not exists movie_search_documents_movie_key_idx
    on movie_search_documents (movie_key, document_type);
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
create_movie_memory_clues_table_sql = """
    create table if not exists movie_memory_clues (
        id bigserial primary key,
        movie_id bigint not null references movies(id) on delete cascade,
        wikipedia_movie_id text not null,
        clue_type text not null,
        source text not null,
        clue_text text not null,
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now()
    );
"""

add_movie_memory_clues_vector_sql = """
    alter table movie_memory_clues
    add column if not exists search_vector tsvector
    generated always as (
        setweight(to_tsvector('english', coalesce(clue_text, '')), 'A')
    ) stored;
"""

create_movie_memory_clues_unique_index_sql = """
    create unique index if not exists movie_memory_clues_source_uidx
    on movie_memory_clues (
        wikipedia_movie_id,
        clue_type,
        source,
        clue_text
    );
"""

create_movie_memory_clues_movie_index_sql = """
    create index if not exists movie_memory_clues_movie_idx
    on movie_memory_clues (movie_id, clue_type);
"""

create_movie_memory_clues_vector_index_sql = """
    create index if not exists movie_memory_clues_vector_idx
    on movie_memory_clues using gin (search_vector);
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
            cur.execute(create_movie_memory_clues_table_sql)
            cur.execute(add_movie_memory_clues_vector_sql)
            cur.execute(create_movie_memory_clues_unique_index_sql)
            cur.execute(create_movie_memory_clues_movie_index_sql)
            cur.execute(create_movie_memory_clues_vector_index_sql)
            cur.execute(add_movie_identity_columns_sql)
            cur.execute(create_movie_key_index_sql)
            cur.execute(add_movie_search_boost_vector_sql)
            cur.execute(create_movie_search_boost_vector_index_sql)
            cur.execute(create_movie_external_ids_table_sql)
            cur.execute(create_movie_external_ids_movie_index_sql)
            cur.execute(backfill_cmu_external_ids_sql)
            cur.execute(backfill_tmdb_external_ids_sql)

            cur.execute(add_movie_search_documents_identity_sql)
            cur.execute(create_movie_search_documents_key_index_sql)
            
        conn.commit()

    print("movies table ready")

if __name__ == "__main__":
    main()
