import argparse

from backend.app.db import get_connection
from backend.app.services.embeddings import (
    embedding_model_name,
    embed_texts,
    normalize_text,
    to_pgvector_literal,
)


default_batch_size = 64
embedding_text_max_chars = 4000


select_documents_sql = """
    select
        document.id,
        document.title,
        document.document_type,
        document.content
    from movie_search_documents document
    left join movie_search_document_embeddings embedding
        on embedding.document_id = document.id
    where embedding.document_id is null
        or embedding.embedding_model is distinct from %(model)s
    order by document.id
    limit %(limit)s;
"""


upsert_embedding_sql = """
    insert into movie_search_document_embeddings (
        document_id,
        embedding,
        embedding_model,
        updated_at
    )
    values (
        %(document_id)s,
        %(embedding)s::vector,
        %(model)s,
        now()
    )
    on conflict (document_id)
    do update set
        embedding = excluded.embedding,
        embedding_model = excluded.embedding_model,
        updated_at = now();
"""


count_remaining_sql = """
    select count(*)
    from movie_search_documents document
    left join movie_search_document_embeddings embedding
        on embedding.document_id = document.id
    where embedding.document_id is null
        or embedding.embedding_model is distinct from %(model)s;
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=default_batch_size)
    return parser.parse_args()


def build_document_embedding_text(
    title: str,
    document_type: str,
    content: str,
) -> str:
    text = f"{title}. {document_type}. {content}"
    return normalize_text(text)[:embedding_text_max_chars]


def fetch_batch(cursor, batch_size: int):
    cursor.execute(
        select_documents_sql,
        {
            "model": embedding_model_name,
            "limit": batch_size,
        },
    )
    return cursor.fetchall()


def update_batch(cursor, rows) -> None:
    texts = [
        build_document_embedding_text(
            title=row[1],
            document_type=row[2],
            content=row[3],
        )
        for row in rows
    ]
    embeddings = embed_texts(texts)

    for row, embedding in zip(rows, embeddings):
        cursor.execute(
            upsert_embedding_sql,
            {
                "document_id": row[0],
                "embedding": to_pgvector_literal(embedding),
                "model": embedding_model_name,
            },
        )


def count_remaining(cursor) -> int:
    cursor.execute(
        count_remaining_sql,
        {
            "model": embedding_model_name,
        },
    )
    return cursor.fetchone()[0]


def main() -> None:
    args = parse_args()

    if args.limit < 0:
        raise ValueError("limit must be zero or greater")

    if args.batch_size < 1:
        raise ValueError("batch size must be at least one")

    processed = 0
    remaining_limit = None if args.limit == 0 else args.limit

    with get_connection() as connection:
        with connection.cursor() as cursor:
            before_count = count_remaining(cursor)
            print(f"documents needing embeddings before run: {before_count}")

            while remaining_limit is None or remaining_limit > 0:
                batch_size = args.batch_size

                if remaining_limit is not None:
                    batch_size = min(batch_size, remaining_limit)

                rows = fetch_batch(cursor, batch_size)

                if not rows:
                    break

                update_batch(cursor, rows)
                connection.commit()

                processed += len(rows)

                if remaining_limit is not None:
                    remaining_limit -= len(rows)

                print(f"processed document embeddings: {processed}")

            after_count = count_remaining(cursor)

    print(f"document embeddings written this run: {processed}")
    print(f"documents needing embeddings after run: {after_count}")


if __name__ == "__main__":
    main()