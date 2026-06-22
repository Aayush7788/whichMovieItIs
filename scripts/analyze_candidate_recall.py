import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from backend.app.services.broad_search import (
    search_movies_broad_full_text,
)
from backend.app.services.hybrid_search import (
    broad_weight,
    minimum_vector_score,
    rank_hybrid_results,
    should_return_no_results,
)
from backend.app.db import get_connection
from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(
            encoding="utf-8",
            errors="replace",
        )


default_qrels_path = Path("data/evaluation/search_qrels.jsonl")
default_output_path = Path("evals/candidate-recall-analysis.json")
default_candidate_limit = 50
default_hit_k = 5
binary_relevance_grade = 2

stop_words = {
    "a",
    "an",
    "and",
    "be",
    "in",
    "is",
    "it",
    "like",
    "of",
    "the",
    "to",
    "with",
}


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--qrels",
        type=Path,
        default=default_qrels_path,
    )
    parser.add_argument(
        "--candidate-limit",
        type=int,
        default=default_candidate_limit,
    )
    parser.add_argument(
        "--hit-k",
        type=int,
        default=default_hit_k,
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=default_output_path,
    )
    return parser.parse_args()


def load_cases(path: Path):
    cases = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            case = json.loads(line)

            required_fields = {"id", "query", "relevant"}
            missing_fields = required_fields - case.keys()

            if missing_fields:
                raise ValueError(
                    f"{path}:{line_number} missing fields: "
                    f"{sorted(missing_fields)}"
                )

            cases.append(case)

    return cases


def result_movie_id(movie):
    return str(movie["wikipedia_movie_id"])


def relevance_by_movie_id(case):
    return {
        str(movie["movie_id"]): int(movie["grade"])
        for movie in case["relevant"]
    }


def fetch_relevant_movies(cases):
    movie_ids = sorted({
        str(movie["movie_id"])
        for case in cases
        for movie in case["relevant"]
    })

    if not movie_ids:
        return {}

    query = """
        select
            wikipedia_movie_id,
            title,
            plot_summary,
            embedding_model
        from movies
        where wikipedia_movie_id = any(%(movie_ids)s::text[]);
    """

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                query,
                {"movie_ids": movie_ids},
            )
            rows = cursor.fetchall()

    return {
        str(row[0]): {
            "movie_id": str(row[0]),
            "title": row[1],
            "plot_summary": row[2],
            "embedding_model": row[3],
        }
        for row in rows
    }


def tokenize(text):
    return re.findall(r"[a-z0-9]+", text.casefold())


def meaningful_query_tokens(query):
    return [
        token
        for token in tokenize(query)
        if token not in stop_words
    ]


def find_relevant_matches(results, relevance):
    matches = []

    for rank, movie in enumerate(results, start=1):
        movie_id = result_movie_id(movie)
        grade = relevance.get(movie_id, 0)

        if grade < binary_relevance_grade:
            continue

        raw_score = movie.get("score")

        matches.append({
            "rank": rank,
            "movie_id": movie_id,
            "title": movie["title"],
            "grade": grade,
            "score": (
                float(raw_score)
                if raw_score is not None
                else None
            ),
        })

    return matches


def first_rank(matches):
    if not matches:
        return None

    return matches[0]["rank"]


def result_snapshot(results, limit=10):
    snapshots = []

    for rank, movie in enumerate(results[:limit], start=1):
        raw_score = movie.get("score")

        snapshots.append({
            "rank": rank,
            "movie_id": result_movie_id(movie),
            "title": movie["title"],
            "score": (
                float(raw_score)
                if raw_score is not None
                else None
            ),
        })

    return snapshots


def build_relevant_movie_evidence(
    case,
    relevant_movies,
):
    query_tokens = meaningful_query_tokens(case["query"])
    evidence = []

    for expected_movie in case["relevant"]:
        movie_id = str(expected_movie["movie_id"])
        database_movie = relevant_movies.get(movie_id)

        if database_movie is None:
            evidence.append({
                "movie_id": movie_id,
                "title": expected_movie["title"],
                "grade": int(expected_movie["grade"]),
                "database_record_found": False,
            })
            continue

        searchable_text = (
            f"{database_movie['title']} "
            f"{database_movie['plot_summary']}"
        )
        searchable_tokens = set(tokenize(searchable_text))

        matched_tokens = [
            token
            for token in query_tokens
            if token in searchable_tokens
        ]
        missing_tokens = [
            token
            for token in query_tokens
            if token not in searchable_tokens
        ]

        evidence.append({
            "movie_id": movie_id,
            "title": database_movie["title"],
            "grade": int(expected_movie["grade"]),
            "database_record_found": True,
            "embedding_model": database_movie["embedding_model"],
            "matched_query_tokens": matched_tokens,
            "missing_query_tokens": missing_tokens,
            "plot_excerpt": database_movie["plot_summary"][:500],
        })

    return evidence


def classify_case(
    case,
    production_rank,
    full_text_matches,
    broad_matches,
    accepted_vector_matches,
    raw_vector_matches,
    guard_suppressed,
    hit_k,
):
    if not case["relevant"]:
        return "no_result_case"

    if production_rank is not None and production_rank <= hit_k:
        return "success"

    accepted_candidate_present = bool(
        full_text_matches
        or broad_matches
        or accepted_vector_matches
    )

    if guard_suppressed and accepted_candidate_present:
        return "guard_suppressed"

    if accepted_candidate_present:
        return "ranking_failure"

    if raw_vector_matches:
        return "vector_threshold_filtered"

    return "candidate_recall_failure"


def review_hint(classification):
    hints = {
        "success": "No investigation required.",
        "no_result_case": "Verify production returned no results.",
        "ranking_failure": (
            "The relevant movie was retrieved but ranked below Hit@K. "
            "Inspect fusion and ranking."
        ),
        "candidate_recall_failure": (
            "The relevant movie was absent from every production candidate source. "
            "Reranking cannot fix this."
        ),
        "vector_threshold_filtered": (
            "Vector search found the movie, but its score was below "
            "the accepted candidate threshold."
        ),
        "guard_suppressed": (
            "The no-result guard removed a query that contained an "
            "accepted relevant candidate."
        ),
    }
    return hints[classification]


def analyze_case(
    case,
    relevant_movies,
    candidate_limit,
    hit_k,
):
    query = case["query"]
    relevance = relevance_by_movie_id(case)

    full_text_results = search_movies(
        query,
        candidate_limit,
    )
    broad_results = search_movies_broad_full_text(
        query,
        candidate_limit,
    )
    raw_vector_results = search_movies_by_embedding(
        query,
        candidate_limit,
    )

    accepted_vector_results = [
        movie
        for movie in raw_vector_results
        if movie.get("score") is not None
        and float(movie["score"]) >= minimum_vector_score
    ]

    guard_suppressed = should_return_no_results(
        full_text_results=full_text_results,
        vector_results=raw_vector_results,
        broad_results=broad_results,
    )

    unguarded_hybrid_results = rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=raw_vector_results,
        broad_results=broad_results,
        limit=candidate_limit,
    )

    production_hybrid_results = (
        []
        if guard_suppressed
        else unguarded_hybrid_results
    )

    full_text_matches = find_relevant_matches(
        full_text_results,
        relevance,
    )
    broad_matches = find_relevant_matches(
        broad_results,
        relevance,
    )
    raw_vector_matches = find_relevant_matches(
        raw_vector_results,
        relevance,
    )
    accepted_vector_matches = find_relevant_matches(
        accepted_vector_results,
        relevance,
    )
    hybrid_matches = find_relevant_matches(
        production_hybrid_results,
        relevance,
    )

    production_rank = first_rank(hybrid_matches)

    classification = classify_case(
        case=case,
        production_rank=production_rank,
        full_text_matches=full_text_matches,
        broad_matches=broad_matches,
        accepted_vector_matches=accepted_vector_matches,
        raw_vector_matches=raw_vector_matches,
        guard_suppressed=guard_suppressed,
        hit_k=hit_k,
    )

    accepted_candidate_present = bool(
        full_text_matches
        or broad_matches
        or accepted_vector_matches
    )
    raw_candidate_present = bool(
        full_text_matches
        or broad_matches
        or raw_vector_matches
    )

    return {
        "id": case["id"],
        "query": query,
        "intent": case.get("intent", "unknown"),
        "classification": classification,
        "review_hint": review_hint(classification),
        "guard_suppressed": guard_suppressed,
        "production_result_count": len(
            production_hybrid_results
        ),
        "candidate_presence": {
            "full_text": bool(full_text_matches),
            "broad_full_text": bool(broad_matches),
            "accepted_vector": bool(accepted_vector_matches),
            "raw_vector": bool(raw_vector_matches),
            "accepted_candidate_pool": accepted_candidate_present,
            "raw_candidate_pool": raw_candidate_present,
        },
        "relevant_ranks": {
            "full_text": first_rank(full_text_matches),
            "broad_full_text": first_rank(broad_matches),
            "raw_vector": first_rank(raw_vector_matches),
            "accepted_vector": first_rank(
                accepted_vector_matches
            ),
            "production_hybrid": production_rank,
        },
        "relevant_matches": {
            "full_text": full_text_matches,
            "broad_full_text": broad_matches,
            "raw_vector": raw_vector_matches,
            "accepted_vector": accepted_vector_matches,
            "production_hybrid": hybrid_matches,
        },
        "relevant_movie_evidence": (
            build_relevant_movie_evidence(
                case,
                relevant_movies,
            )
        ),
        "top_results": {
            "full_text": result_snapshot(full_text_results),
            "broad_full_text": result_snapshot(broad_results),
            "raw_vector": result_snapshot(raw_vector_results),
            "production_hybrid": result_snapshot(
                production_hybrid_results
            ),
        },
    }


def metric(numerator, denominator):
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": (
            numerator / denominator
            if denominator
            else None
        ),
    }


def summarize(analyses, hit_k):
    ranked_cases = [
        analysis
        for analysis in analyses
        if analysis["classification"] != "no_result_case"
    ]
    no_result_cases = [
        analysis
        for analysis in analyses
        if analysis["classification"] == "no_result_case"
    ]

    classification_counts = Counter(
        analysis["classification"]
        for analysis in analyses
    )

    by_intent = {}

    for analysis in analyses:
        intent = analysis["intent"]
        by_intent.setdefault(intent, Counter())
        by_intent[intent][analysis["classification"]] += 1

    accepted_candidate_count = sum(
        analysis["candidate_presence"]["accepted_candidate_pool"]
        for analysis in ranked_cases
    )
    raw_candidate_count = sum(
        analysis["candidate_presence"]["raw_candidate_pool"]
        for analysis in ranked_cases
    )
    production_hit_count = sum(
        analysis["relevant_ranks"]["production_hybrid"]
        is not None
        and analysis["relevant_ranks"]["production_hybrid"] <= hit_k
        for analysis in ranked_cases
    )
    correct_no_result_count = sum(
        analysis["production_result_count"] == 0
        for analysis in no_result_cases
    )

    return {
        "cases": len(analyses),
        "ranked_cases": len(ranked_cases),
        "no_result_cases": len(no_result_cases),
        "classification_counts": dict(
            sorted(classification_counts.items())
        ),
        "classification_counts_by_intent": {
            intent: dict(sorted(counts.items()))
            for intent, counts in sorted(by_intent.items())
        },
        "accepted_candidate_recall": metric(
            accepted_candidate_count,
            len(ranked_cases),
        ),
        "raw_candidate_recall": metric(
            raw_candidate_count,
            len(ranked_cases),
        ),
        f"production_hit@{hit_k}": metric(
            production_hit_count,
            len(ranked_cases),
        ),
        "no_result_correct": metric(
            correct_no_result_count,
            len(no_result_cases),
        ),
    }


def print_metric(name, value):
    print(
        f"{name}: "
        f"{value['value']:.4f} "
        f"({value['numerator']}/{value['denominator']})"
    )


def main():
    args = parse_args()

    cases = load_cases(args.qrels)
    relevant_movies = fetch_relevant_movies(cases)
    
    analyses = [
        analyze_case(
            case=case,
            relevant_movies=relevant_movies,
            candidate_limit=args.candidate_limit,
            hit_k=args.hit_k,
        )
        for case in cases
    ]

    summary = summarize(
        analyses=analyses,
        hit_k=args.hit_k,
    )

    report = {
        "qrels": str(args.qrels),
        "candidate_limit": args.candidate_limit,
        "hit_k": args.hit_k,
        "minimum_vector_score": minimum_vector_score,
        "summary": summary,
        "cases": analyses,
        "broad_weight": broad_weight,
    }

    args.json_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.json_out.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"cases: {summary['cases']}")
    print(f"ranked cases: {summary['ranked_cases']}")

    print_metric(
        "accepted candidate recall",
        summary["accepted_candidate_recall"],
    )
    print_metric(
        "raw candidate recall",
        summary["raw_candidate_recall"],
    )
    print_metric(
        f"production hit@{args.hit_k}",
        summary[f"production_hit@{args.hit_k}"],
    )
    print_metric(
        "no-result correct",
        summary["no_result_correct"],
    )

    print("\nclassifications:")

    for classification, count in (
        summary["classification_counts"].items()
    ):
        print(f"- {classification}: {count}")

    print("\nfailed ranked cases:")

    for analysis in analyses:
        if analysis["classification"] in {
            "success",
            "no_result_case",
        }:
            continue

        print(
            f"- {analysis['id']} "
            f"[{analysis['classification']}]: "
            f"{analysis['query']}"
        )

    print(f"\nwrote {args.json_out}")


if __name__ == "__main__":
    main()