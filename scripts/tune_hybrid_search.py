import json
from itertools import product
from pathlib import Path

from backend.app.services.hybrid_search import (
    full_text_weight,
    get_candidate_limit,
    minimum_vector_score,
    minimum_vector_only_score,
    rank_hybrid_results,
    rrf_k,
    should_return_no_results,
    vector_weight,
)
from backend.app.services.search import search_movies
from backend.app.services.vector_search import search_movies_by_embedding
from scripts.evaluate_search import (
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
    "evals/hybrid-tuning-results.json"
)

result_limit = 10
candidate_limit = get_candidate_limit(result_limit)

rrf_k_values = [20, 40, 60, 80]
minimum_vector_score_values = [0.30, 0.35, 0.40, 0.45]
full_text_weight_values = [1.0, 1.5, 2.0]
vector_weight_values = [1.0, 1.5, 2.0, 2.5, 3.0]

current_config = {
    "rrf_k": rrf_k,
    "minimum_vector_score": minimum_vector_score,
    "full_text_weight": full_text_weight,
    "vector_weight": vector_weight,
}

spotlight_case_ids = {
    "q005_no_result_noise",
    "q009_event_ship_iceberg",
    "q013_semantic_time_car",
}


def build_configs():
    return [
        {
            "rrf_k": rrf_k_value,
            "minimum_vector_score": minimum_vector_score_value,
            "full_text_weight": full_text_weight_value,
            "vector_weight": vector_weight_value,
        }
        for (
            rrf_k_value,
            minimum_vector_score_value,
            full_text_weight_value,
            vector_weight_value,
        ) in product(
            rrf_k_values,
            minimum_vector_score_values,
            full_text_weight_values,
            vector_weight_values,
        )
    ]


def collect_candidates(cases):
    cached_cases = []

    for case in cases:
        query = case["query"]

        print(f"collecting candidates: {query}")

        cached_cases.append(
            {
                "case": case,
                "full_text_results": search_movies(
                    query,
                    candidate_limit,
                ),
                "vector_results": search_movies_by_embedding(
                    query,
                    candidate_limit,
                ),
            }
        )

    return cached_cases


def evaluate_cached_case(cached_case, config):
    case = cached_case["case"]

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
        results = []
    else:
        results = rank_hybrid_results(
            full_text_results=full_text_results,
            vector_results=vector_results,
            limit=result_limit,
            rrf_k_value=config["rrf_k"],
            minimum_vector_score_value=config[
                "minimum_vector_score"
            ],
            full_text_weight_value=config[
                "full_text_weight"
            ],
            vector_weight_value=config[
                "vector_weight"
            ],
        )

    relevance = relevance_by_movie_id(case)
    no_result_expected = len(relevance) == 0

    if no_result_expected:
        no_result_correct = len(results) == 0
    else:
        no_result_correct = None

    return {
        "id": case["id"],
        "query": case["query"],
        "result_ids": [
            result_movie_id(movie)
            for movie in results
        ],
        "result_titles": [
            movie["title"]
            for movie in results
        ],
        "hit@5": hit_at(results, relevance, 5),
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
        "no_result_correct": no_result_correct,
        "latency_ms": 0.0,
    }


def compact_summary(summary):
    return {
        "cases": summary["cases"],
        "hit@5": summary["hit@5"],
        "mrr@10": summary["mrr@10"],
        "recall@10": summary["recall@10"],
        "ndcg@10": summary["ndcg@10"],
        "no_result_correct": summary[
            "no_result_correct"
        ],
    }


def evaluate_config(cached_cases, config):
    reports = [
        evaluate_cached_case(
            cached_case=cached_case,
            config=config,
        )
        for cached_case in cached_cases
    ]

    summary = summarize_reports(
        mode_name="hybrid",
        reports=reports,
    )

    spotlight = {
        report["id"]: {
            "query": report["query"],
            "result_ids": report["result_ids"],
            "result_titles": report["result_titles"],
            "hit@5": report["hit@5"],
            "mrr@10": report["mrr@10"],
            "ndcg@10": report["ndcg@10"],
            "no_result_correct": report[
                "no_result_correct"
            ],
        }
        for report in reports
        if report["id"] in spotlight_case_ids
    }

    return {
        "config": config,
        "summary": compact_summary(summary),
        "spotlight": spotlight,
    }


def metric_value(summary, metric):
    value = summary.get(metric)

    if value is None:
        return 0.0

    return float(value)


def ranking_key(row):
    summary = row["summary"]

    return (
        metric_value(summary, "no_result_correct"),
        metric_value(summary, "hit@5"),
        metric_value(summary, "ndcg@10"),
        metric_value(summary, "mrr@10"),
        metric_value(summary, "recall@10"),
    )


def find_config_row(rows, expected_config):
    for row in rows:
        if row["config"] == expected_config:
            return row

    raise ValueError(
        f"Configuration was not evaluated: {expected_config}"
    )


def choose_recommendation(best_row, baseline_row):
    best_summary = best_row["summary"]
    baseline_summary = baseline_row["summary"]

    no_result_is_safe = (
        metric_value(
            best_summary,
            "no_result_correct",
        )
        >= metric_value(
            baseline_summary,
            "no_result_correct",
        )
    )

    hit_improved = (
        metric_value(best_summary, "hit@5")
        > metric_value(baseline_summary, "hit@5")
    )

    ndcg_improvement = (
        metric_value(best_summary, "ndcg@10")
        - metric_value(
            baseline_summary,
            "ndcg@10",
        )
    )

    meaningful_ndcg_improvement = (
        ndcg_improvement >= 0.01
    )

    if no_result_is_safe and (
        hit_improved
        or meaningful_ndcg_improvement
    ):
        return "review_best_config"

    return "keep_current_config"


def print_result(label, row):
    print(label)
    print(
        json.dumps(
            {
                "config": row["config"],
                "summary": row["summary"],
                "spotlight": row["spotlight"],
            },
            indent=2,
        )
    )
    print()


def main():
    cases = load_cases()
    configs = build_configs()

    print(
        f"testing {len(configs)} hybrid configurations"
    )
    print()

    cached_cases = collect_candidates(cases)

    print()
    print("evaluating cached candidates")
    print()

    rows = [
        evaluate_config(
            cached_cases=cached_cases,
            config=config,
        )
        for config in configs
    ]

    rows.sort(
        key=ranking_key,
        reverse=True,
    )

    best_row = rows[0]

    baseline_row = find_config_row(
        rows=rows,
        expected_config=current_config,
    )

    recommendation = choose_recommendation(
        best_row=best_row,
        baseline_row=baseline_row,
    )

    output = {
        "result_limit": result_limit,
        "candidate_limit": candidate_limit,
        "minimum_vector_only_score": minimum_vector_only_score,
        "tested_configurations": len(configs),
        "recommendation": recommendation,
        "baseline": baseline_row,
        "best": best_row,
        "top_10": rows[:10],
    }

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(output, indent=2),
        encoding="utf-8",
    )

    print_result("current configuration:", baseline_row)
    print_result("mathematical best:", best_row)

    print(f"recommendation: {recommendation}")
    print(f"wrote: {output_path}")


if __name__ == "__main__":
    main()