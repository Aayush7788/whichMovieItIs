import json
from pathlib import Path
from time import perf_counter

from backend.app.services.broad_search import (
    search_movies_broad_full_text,
)
from backend.app.services.hybrid_search import (
    add_ranked_results,
    full_text_weight,
    minimum_vector_score,
    rank_hybrid_results,
    should_return_no_results,
    vector_weight,
)
from backend.app.services.search import search_movies
from backend.app.services.vector_search import (
    search_movies_by_embedding,
)
from scripts.evaluate_search import (
    binary_relevance_grade,
    hit_at,
    load_cases,
    ndcg_at,
    recall_at,
    reciprocal_rank_at,
    relevance_by_movie_id,
    result_movie_id,
    summarize_reports,
)


output_path = Path(
    "evals/broad-hybrid-experiment.json"
)

candidate_limit = 50
result_limit = 10

broad_weight_values = [
    0.5,
    1.0,
    1.5,
    2.0,
    2.5,
    3.0,
    3.5,
    4.0,
]


def collect_candidates(cases):
    cached_cases = []

    for case in cases:
        query = case["query"]

        print(f"collecting candidates: {query}")

        started_at = perf_counter()
        broad_results = search_movies_broad_full_text(
            query,
            candidate_limit,
        )
        broad_latency_ms = (
            perf_counter() - started_at
        ) * 1000

        cached_cases.append({
            "case": case,
            "full_text_results": search_movies(
                query,
                candidate_limit,
            ),
            "vector_results": search_movies_by_embedding(
                query,
                candidate_limit,
            ),
            "broad_results": broad_results,
            "broad_latency_ms": broad_latency_ms,
        })

    return cached_cases


def sort_combined_results(combined, limit):
    results = sorted(
        combined.values(),
        key=lambda movie: (
            -float(movie["score"]),
            str(movie["title"]),
        ),
    )
    return results[:limit]


def rank_broad_hybrid(
    full_text_results,
    vector_results,
    broad_results,
    broad_weight,
):
    combined = {}

    add_ranked_results(
        combined=combined,
        results=full_text_results,
        weight=full_text_weight,
    )

    add_ranked_results(
        combined=combined,
        results=vector_results,
        minimum_score=minimum_vector_score,
        weight=vector_weight,
    )

    add_ranked_results(
        combined=combined,
        results=broad_results,
        weight=broad_weight,
    )

    return sort_combined_results(
        combined,
        result_limit,
    )


def baseline_results(cached_case):
    full_text_results = cached_case[
        "full_text_results"
    ]
    vector_results = cached_case[
        "vector_results"
    ]

    if should_return_no_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
    ):
        return []

    return rank_hybrid_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
        limit=result_limit,
    )


def experimental_results(
    cached_case,
    broad_weight,
):
    full_text_results = cached_case[
        "full_text_results"
    ]
    vector_results = cached_case[
        "vector_results"
    ]
    broad_results = cached_case[
        "broad_results"
    ]

    guard_suppressed = should_return_no_results(
        full_text_results=full_text_results,
        vector_results=vector_results,
    )

    if guard_suppressed and not broad_results:
        return []

    return rank_broad_hybrid(
        full_text_results=full_text_results,
        vector_results=vector_results,
        broad_results=broad_results,
        broad_weight=broad_weight,
    )

def accepted_candidate_ids(
    cached_case,
    include_broad,
):
    movie_ids = {
        result_movie_id(movie)
        for movie in cached_case["full_text_results"]
    }

    movie_ids.update({
        result_movie_id(movie)
        for movie in cached_case["vector_results"]
        if movie.get("score") is not None
        and float(movie["score"])
        >= minimum_vector_score
    })

    if include_broad:
        movie_ids.update({
            result_movie_id(movie)
            for movie in cached_case["broad_results"]
        })

    return movie_ids


def candidate_recall(cached_cases, include_broad):
    ranked_cases = 0
    candidate_hits = 0

    for cached_case in cached_cases:
        case = cached_case["case"]
        relevance = relevance_by_movie_id(case)

        acceptable_ids = {
            movie_id
            for movie_id, grade in relevance.items()
            if grade >= binary_relevance_grade
        }

        if not acceptable_ids:
            continue

        ranked_cases += 1

        candidate_ids = accepted_candidate_ids(
            cached_case,
            include_broad,
        )

        if acceptable_ids & candidate_ids:
            candidate_hits += 1

    return {
        "numerator": candidate_hits,
        "denominator": ranked_cases,
        "value": candidate_hits / ranked_cases,
    }


def build_report(case, results):
    relevance = relevance_by_movie_id(case)
    no_result_expected = len(relevance) == 0

    return {
        "id": case["id"],
        "query": case["query"],
        "intent": case.get("intent", "unknown"),
        "result_ids": [
            result_movie_id(movie)
            for movie in results
        ],
        "result_titles": [
            movie["title"]
            for movie in results
        ],
        "hit@5": hit_at(
            results,
            relevance,
            5,
        ),
        "mrr@10": reciprocal_rank_at(
            results,
            relevance,
            10,
        ),
        "recall@10": recall_at(
            results,
            relevance,
            10,
        ),
        "ndcg@10": ndcg_at(
            results,
            relevance,
            10,
        ),
        "no_result_correct": (
            len(results) == 0
            if no_result_expected
            else None
        ),
        "latency_ms": 0.0,
    }


def compact_summary(summary):
    return {
        "hit@5": summary["hit@5"],
        "mrr@10": summary["mrr@10"],
        "recall@10": summary["recall@10"],
        "ndcg@10": summary["ndcg@10"],
        "no_result_correct": (
            summary["no_result_correct"]
        ),
    }


def evaluate_configuration(
    cached_cases,
    broad_weight=None,
):
    include_broad = broad_weight is not None
    reports = []

    for cached_case in cached_cases:
        case = cached_case["case"]

        if include_broad:
            results = experimental_results(
                cached_case,
                broad_weight,
            )
        else:
            results = baseline_results(cached_case)

        reports.append(
            build_report(case, results)
        )

    mode_name = (
        "broad-hybrid"
        if include_broad
        else "baseline-hybrid"
    )

    summary = summarize_reports(
        mode_name,
        reports,
    )

    return {
        "broad_weight": broad_weight,
        "summary": compact_summary(summary),
        "candidate_recall": candidate_recall(
            cached_cases,
            include_broad,
        ),
        "reports": reports,
    }


def metric_value(row, metric):
    value = row["summary"].get(metric)
    return float(value or 0.0)


def ranking_key(row):
    return (
        metric_value(row, "no_result_correct"),
        metric_value(row, "hit@5"),
        metric_value(row, "ndcg@10"),
        metric_value(row, "mrr@10"),
        metric_value(row, "recall@10"),
    )


def choose_recommendation(
    baseline,
    experimental_rows,
):
    safe_rows = []

    for row in experimental_rows:
        summary = row["summary"]
        baseline_summary = baseline["summary"]

        no_result_safe = (
            summary["no_result_correct"]
            >= baseline_summary["no_result_correct"]
        )

        hit_improved = (
            summary["hit@5"]
            > baseline_summary["hit@5"]
        )

        other_metrics_safe = all(
            summary[metric]
            >= baseline_summary[metric]
            for metric in (
                "mrr@10",
                "recall@10",
                "ndcg@10",
            )
        )

        if (
            no_result_safe
            and hit_improved
            and other_metrics_safe
        ):
            safe_rows.append(row)

    if not safe_rows:
        return None

    return max(
        safe_rows,
        key=ranking_key,
    )


def changed_cases(baseline, recommendation):
    if recommendation is None:
        return {
            "improved": [],
            "regressed": [],
        }

    baseline_reports = {
        report["id"]: report
        for report in baseline["reports"]
    }

    recommended_reports = {
        report["id"]: report
        for report in recommendation["reports"]
    }

    improved = []
    regressed = []

    for case_id, baseline_report in (
        baseline_reports.items()
    ):
        recommended_report = (
            recommended_reports[case_id]
        )

        baseline_hit = baseline_report["hit@5"]
        recommended_hit = (
            recommended_report["hit@5"]
        )

        if not baseline_hit and recommended_hit:
            improved.append(case_id)
        elif baseline_hit and not recommended_hit:
            regressed.append(case_id)

    return {
        "improved": improved,
        "regressed": regressed,
    }

def main():
    cases = load_cases()
    cached_cases = collect_candidates(cases)

    baseline = evaluate_configuration(
        cached_cases,
    )

    experimental_rows = [
        evaluate_configuration(
            cached_cases,
            broad_weight=broad_weight,
        )
        for broad_weight in broad_weight_values
    ]

    recommendation = choose_recommendation(
        baseline,
        experimental_rows,
    )

    changes = changed_cases(
        baseline,
        recommendation,
    )

    broad_latencies = [
        cached_case["broad_latency_ms"]
        for cached_case in cached_cases
    ]

    output = {
        "candidate_limit": candidate_limit,
        "result_limit": result_limit,
        "tested_broad_weights": (
            broad_weight_values
        ),
        "baseline": baseline,
        "experiments": experimental_rows,
        "recommendation": recommendation,
        "changed_cases": changes,
        "broad_latency_ms": {
            "average": (
                sum(broad_latencies)
                / len(broad_latencies)
            ),
            "maximum": max(broad_latencies),
        },
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_path.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print("baseline:")
    print(
        json.dumps(
            {
                "summary": baseline["summary"],
                "candidate_recall": (
                    baseline["candidate_recall"]
                ),
            },
            indent=2,
        )
    )

    print("\nrecommendation:")

    if recommendation is None:
        print("keep current production hybrid")
    else:
        print(
            json.dumps(
                {
                    "broad_weight": (
                        recommendation[
                            "broad_weight"
                        ]
                    ),
                    "summary": (
                        recommendation["summary"]
                    ),
                    "candidate_recall": (
                        recommendation[
                            "candidate_recall"
                        ]
                    ),
                    "changed_cases": changes,
                },
                indent=2,
            )
        )

    print(f"\nwrote: {output_path}")


if __name__ == "__main__":
    main()