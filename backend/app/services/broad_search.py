import re

from backend.app.db import get_connection


maximum_required_matches = 3

token_pattern = re.compile(r"[a-z0-9]+")

broad_search_sql = """
    with query_terms as (
        select distinct
            plainto_tsquery(
                'english',
                query_term.term
            ) as query
        from unnest(
            %(terms)s::text[]
        ) as query_term(term)
        where plainto_tsquery(
            'english',
            query_term.term
        ) <> ''::tsquery
    ),
    candidate_matches as (
        select
            movie.id,
            count(*)::integer as matched_terms,
            sum(
                ts_rank_cd(
                    movie.search_vector,
                    query_terms.query
                )
            )::double precision as score
        from query_terms
        join movies movie
            on movie.search_vector @@ query_terms.query
        group by movie.id
    )
    select
        movie.wikipedia_movie_id,
        movie.title,
        movie.release_date,
        movie.genres,
        movie.plot_summary,
        candidate_matches.score
    from candidate_matches
    join movies movie
        on movie.id = candidate_matches.id
    where candidate_matches.matched_terms >= least(
        %(maximum_required_matches)s,
        (
            select count(*)
            from query_terms
        )
    )
    order by
        candidate_matches.matched_terms desc,
        candidate_matches.score desc,
        movie.title
    limit %(limit)s;
"""


def extract_search_terms(query: str) -> list[str]:
    terms = token_pattern.findall(query.casefold())
    return list(dict.fromkeys(terms))


def search_movies_broad_full_text(
    query: str,
    limit: int = 5,
) -> list[dict[str, object]]:
    terms = extract_search_terms(query)

    if not terms:
        return []

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                broad_search_sql,
                {
                    "terms": terms,
                    "maximum_required_matches": (
                        maximum_required_matches
                    ),
                    "limit": limit,
                },
            )
            rows = cursor.fetchall()

    return [
        {
            "wikipedia_movie_id": row[0],
            "title": row[1],
            "release_date": row[2],
            "genres": row[3],
            "plot_summary": row[4],
            "score": (
                float(row[5])
                if row[5] is not None
                else None
            ),
        }
        for row in rows
    ]