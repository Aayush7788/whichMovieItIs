import argparse
import json
from pathlib import Path

from scripts.evaluate_search import (
    evaluate_case,
    load_cases,
    relevance_by_movie_id,
    search_modes,
    summarize_reports,
)


default_json_out = Path(
    "evals/day21-hybrid-v2-regressions.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", default="hybrid")
    parser.add_argument("--candidate", default="hybrid-v2")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json-out", type=Path, default=default_json_out)
    return parser.parse_args()


def first_relevant_rank(
    result_ids: list[str],
    relevance: dict[str, int],
) -> int | None:
    for rank, movie_id in enumerate(result_ids, start=1):
        if relevance.get(movie_id, 0) >= 2:
            return rank

    return None


def case_passed(report: dict[str, object]) -> bool:
    if report["no_result_correct"] is not None:
        return bool(report["no_result_correct"])

    return bool(report["hit@5"])


def compare_case(
    case: dict[str, object],
    baseline_report: dict[str, object],
    candidate_report: dict[str, object],
) -> dict[str, object]:
    relevance = relevance_by_movie_id(case)

    baseline_rank = first_relevant_rank(
        baseline_report["result_ids"],
        relevance,
    )
    candidate_rank = first_relevant_rank(
        candidate_report["result_ids"],
        relevance,
    )

    baseline_passed = case_passed(baseline_report)
    candidate_passed = case_passed(candidate_report)

    if baseline_passed and not candidate_passed:
        status = "regression"
    elif not baseline_passed and candidate_passed:
        status = "improvement"
    elif baseline_passed and candidate_passed:
        status = "same_pass"
    else:
        status = "same_fail"

    return {
        "id": case["id"],
        "intent": case.get("intent", "unknown"),
        "query": case["query"],
        "status": status,
        "baseline_passed": baseline_passed,
        "candidate_passed": candidate_passed,
        "baseline_first_relevant_rank": baseline_rank,
        "candidate_first_relevant_rank": candidate_rank,
        "baseline_titles": baseline_report["result_titles"][:5],
        "candidate_titles": candidate_report["result_titles"][:5],
    }


def main() -> int:
    args = parse_args()

    if args.baseline not in search_modes:
        raise ValueError(f"unknown baseline mode: {args.baseline}")

    if args.candidate not in search_modes:
        raise ValueError(f"unknown candidate mode: {args.candidate}")

    cases = load_cases()

    baseline_reports = [
        evaluate_case(
            case=case,
            search_function=search_modes[args.baseline],
            result_limit=args.limit,
        )
        for case in cases
    ]
    candidate_reports = [
        evaluate_case(
            case=case,
            search_function=search_modes[args.candidate],
            result_limit=args.limit,
        )
        for case in cases
    ]

    case_comparisons = [
        compare_case(
            case=case,
            baseline_report=baseline_report,
            candidate_report=candidate_report,
        )
        for case, baseline_report, candidate_report
        in zip(cases, baseline_reports, candidate_reports)
    ]

    status_counts: dict[str, int] = {}

    for comparison in case_comparisons:
        status = comparison["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    report = {
        "baseline": args.baseline,
        "candidate": args.candidate,
        "limit": args.limit,
        "baseline_summary": summarize_reports(
            args.baseline,
            baseline_reports,
        ),
        "candidate_summary": summarize_reports(
            args.candidate,
            candidate_reports,
        ),
        "status_counts": dict(sorted(status_counts.items())),
        "cases": case_comparisons,
    }

    args.json_out.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    args.json_out.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("mode regression analysis")
    print(f"baseline: {args.baseline}")
    print(f"candidate: {args.candidate}")
    print(f"status counts: {report['status_counts']}")
    print(f"wrote: {args.json_out}")

    print()
    print("regressions:")

    for comparison in case_comparisons:
        if comparison["status"] == "regression":
            print(
                f"- {comparison['id']} "
                f"[{comparison['intent']}]: "
                f"{comparison['query']}"
            )

    print()
    print("improvements:")

    for comparison in case_comparisons:
        if comparison["status"] == "improvement":
            print(
                f"- {comparison['id']} "
                f"[{comparison['intent']}]: "
                f"{comparison['query']}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())