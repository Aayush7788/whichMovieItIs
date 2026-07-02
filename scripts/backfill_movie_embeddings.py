import argparse

from backend.app.db import get_connection
from backend.app.services.embeddings import (
    embedding_model_name,
    build_movie_embedding_text,
    embed_texts,
    to_pgvector_literal,
)

default_batch_size = 64

select_movie_sql = """
    select id, title, plot_summary, search_boost_text
    from movies
    where search_embedding is null
        or embedding_model is distinct from %(model)s
    order by id
    limit %(limit)s;
"""

update_embedding_sql = """
    update movies 
    set search_embedding = %(embedding)s::vector,
        embedding_model = %(model)s
    where id = %(id)s;
"""

count_remaining_sql = """
    select count(*)
    from movies
    where search_embedding is null
        or embedding_model is distinct from %(model)s;
"""

def fetch_batch(cur, batch_size:int):
    cur.execute(
        select_movie_sql,
        {
            "model": embedding_model_name,
            "limit": batch_size,
        },
    )

    return cur.fetchall()

def update_batch(cur, rows):
    texts = [
        build_movie_embedding_text(
            title=row[1],
            plot_summary=row[2],
            search_boost_text=row[3] or "",
        )
        for row in rows
    ]
    embeddings = embed_texts(texts)

    for row, embedding in zip(rows, embeddings):
        cur.execute(
            update_embedding_sql,
            {
                "id": row[0],
                "embedding": to_pgvector_literal(embedding),
                "model": embedding_model_name,
            },
        )

def count_remaining(cur)-> int:
    cur.execute(count_remaining_sql, {"model": embedding_model_name})
    return cur.fetchone()[0]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=default_batch_size)
    args = parser.parse_args()

    processed = 0
    remaining_limit = args.limit

    with get_connection() as conn:
        with conn.cursor() as cur:
            before_count = count_remaining(cur)
            print(f"movies needing embeddings before run: {before_count}")

            while True:
                if remaining_limit == 0:
                    break

                batch_size = args.batch_size

                if remaining_limit is not None:
                    batch_size = min(batch_size, remaining_limit)

                rows = fetch_batch(cur, batch_size)

                if not rows:
                    break

                update_batch(cur, rows)
                conn.commit()

                processed+=len(rows)

                if remaining_limit is not None:
                    remaining_limit -= len(rows)

                print(f"processed embedding: {processed}")
            
            after_count = count_remaining(cur)
    
    print(f"movies embedded this run: {processed}")
    print(f"movies needing embeddings after run: {after_count}")


if __name__ == "__main__":
    main()
