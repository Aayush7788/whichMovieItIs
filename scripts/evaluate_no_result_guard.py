import json
from pathlib import Path

from backend.app.services.hybrid_search import (
    get_candidate_limit,
    rank_hybrid_results,
    should_return_no_results,
)
from backend.app.services.search import search_movies
from backend.app.services.vector_search import (
    search_movies_by_embedding,
)
from scripts.evaluate_search import (
    evaluate_case,
    load_cases,
    summarize_reports,
)

output_path = Path(
    "evals/no-result-guard-evaluation.json"
)

result_limit = 10

threshold_values = [
    0.40,
    0.45,
    0.46,
    0.47,
    0.48,
    0.50,
    0.52,
    0.54,
    0.56,
]

ranking_metrics = [
    "hit@5",
    "mrr@10",
    "recall@10",
    "ndcg@10",
]


def collect_candidates(cases):
    candidate_limit = get_candidate_limit(
        result_limit
    )

    cached_candidates = {}

    for case in cases:
        query = case["query"]

        print(f"collecting candidates: {query}")

        cached_candidates[query] = {
            "full_text_results": search_movies(
                query,
                candidate_limit,
            ),
            "vector_results": search_movies_by_embedding(
                query,
                candidate_limit,
            ),
        }

    return cached_candidates


def build_search_function(
    cached_candidates,
    threshold,
):
    def search_with_guard(query, limit=10):
        candidates = cached_candidates[query]

        full_text_results = candidates[
            "full_text_results"
        ]

        vector_results = candidates[
            "vector_results"
        ]

        if should_return_no_results(
            full_text_results=full_text_results,
            vector_results=vector_results,
            minimum_vector_only_score_value=threshold,
        ):
            return []

        return rank_hybrid_results(
            full_text_results=full_text_results,
            vector_results=vector_results,
            limit=limit,
        )

    return search_with_guard


def compact_summary(summary):
    return {
        "cases": summary["cases"],
        "ranked_cases": summary["ranked_cases"],
        "no_result_cases": summary[
            "no_result_cases"
        ],
        "hit@5": summary["hit@5"],
        "mrr@10": summary["mrr@10"],
        "recall@10": summary["recall@10"],
        "ndcg@10": summary["ndcg@10"],
        "no_result_correct": summary[
            "no_result_correct"
        ],
    }


def evaluate_threshold(
    cases,
    cached_candidates,
    threshold,
):
    search_function = build_search_function(
        cached_candidates=cached_candidates,
        threshold=threshold,
    )

    reports = [
        evaluate_case(
            case=case,
            search_function=search_function,
            result_limit=result_limit,
        )
        for case in cases
    ]

    summary = summarize_reports(
        mode_name="guarded-hybrid",
        reports=reports,
    )

    no_result_failures = [
        report["id"]
        for report in reports
        if report["no_result_correct"] is False
    ]

    suppressed_cases = [
        report["id"]
        for report in reports
        if len(report["result_ids"]) == 0
    ]

    suppressed_relevant_cases = [
        report["id"]
        for report in reports
        if report["no_result_correct"] is None
        and len(report["result_ids"]) == 0
    ]

    return {
        "threshold": threshold,
        "summary": compact_summary(summary),
        "no_result_failures": no_result_failures,
        "suppressed_cases": suppressed_cases,
        "suppressed_relevant_cases": (
            suppressed_relevant_cases
        ),
    }


def metric_value(summary, metric):
    value = summary.get(metric)

    if value is None:
        return 0.0

    return float(value)


def ranking_is_not_worse(
    candidate_summary,
    baseline_summary,
):
    return all(
        metric_value(candidate_summary, metric)
        >= metric_value(baseline_summary, metric)
        for metric in ranking_metrics
    )


def choose_recommendation(rows):
    baseline_row = rows[0]
    baseline_summary = baseline_row["summary"]

    for row in rows:
        summary = row["summary"]

        if summary["no_result_correct"] != 1.0:
            continue

        if ranking_is_not_worse(
            candidate_summary=summary,
            baseline_summary=baseline_summary,
        ):
            return row

    return None


def print_row(label, row):
    print(label)
    print(
        json.dumps(
            {
                "threshold": row["threshold"],
                "summary": row["summary"],
                "no_result_failures": row[
                    "no_result_failures"
                ],
                "suppressed_relevant_cases": row[
                    "suppressed_relevant_cases"
                ],
            },
            indent=2,
        )
    )
    print()


def main():
    cases = load_cases()

    cached_candidates = collect_candidates(cases)

    print()
    print("evaluating thresholds")
    print()

    rows = [
        evaluate_threshold(
            cases=cases,
            cached_candidates=cached_candidates,
            threshold=threshold,
        )
        for threshold in threshold_values
    ]

    recommendation = choose_recommendation(rows)

    output = {
        "result_limit": result_limit,
        "tested_thresholds": threshold_values,
        "baseline": rows[0],
        "recommendation": recommendation,
        "results": rows,
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print_row("baseline:", rows[0])

    if recommendation is None:
        print("recommendation: no safe threshold")
    else:
        print_row(
            "recommended:",
            recommendation,
        )

    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()