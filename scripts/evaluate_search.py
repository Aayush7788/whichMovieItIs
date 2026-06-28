import json
import sys
from pathlib import Path
import argparse
from backend.app.services.hybrid_search import search_movies_hybrid
from backend.app.services.vector_search import search_movies_by_embedding
from backend.app.services.search import search_movies
from backend.app.services.reranker import search_movies_reranked
from math import log2
from time import perf_counter
from backend.app.services.document_search import search_movies_document_hybrid
from backend.app.services.hybrid_v2_search import search_movies_hybrid_v2

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(
            encoding="utf-8",
            errors="replace",
        )

eval_file = Path("data/evaluation/search_qrels.jsonl")
default_limit = 10
binary_relevance_grade = 2

search_modes = {
    "full-text": search_movies,
    "vector": search_movies_by_embedding,
    "hybrid": search_movies_hybrid,
    "reranked": search_movies_reranked,
    "document-hybrid": search_movies_document_hybrid,
    "hybrid-v2": search_movies_hybrid_v2,
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=search_modes.keys(), default="hybrid")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--limit", type=int, default=default_limit)
    parser.add_argument("--qrels", type=Path, default=eval_file)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()

def load_cases(path: Path = eval_file):
    cases = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            case  = json.loads(line)

            if "id" not in case or "query" not in case or "relevant" not in case:
                raise ValueError(
                        f"{path}:{line_number} must include id, query and relevant"
                    )
            
            cases.append(case)
    
    return cases

def relevance_by_movie_id(case):
    return{
        str(item["movie_id"]): int(item["grade"])
        for item in case["relevant"]
            
    }

def result_movie_id(movie):
    return str(movie["wikipedia_movie_id"])

def hit_at(results, relevance, k):
    return any(
        relevance.get(result_movie_id(movie), 0) >=
        binary_relevance_grade
        for movie in results[:k]
    )

def reciprocal_rank_at(results, relevance, k):
    for rank, movie in enumerate(results[:k], start=1):
        if relevance.get(result_movie_id(movie), 0) >= binary_relevance_grade:
            return 1 / rank
    return 0.0

def recall_at(results, relevance, k):
    relevant_ids = {
        movie_id 
        for movie_id, grade in relevance.items()
        if grade >=binary_relevance_grade
    }

    if not relevant_ids:
        return None
    
    found_ids = {
        result_movie_id(movie)
        for movie in results[:k]
        if relevance.get(result_movie_id(movie), 0) >=
        binary_relevance_grade
    }
    return len(found_ids) / len(relevant_ids)

def dcg(grades):
    return sum(
        ((2 ** grade) - 1) / log2(rank + 1)
        for rank, grade in enumerate(grades, start=1)
    )

def ndcg_at(results, relevance, k):
    actual_grades = [
        relevance.get(result_movie_id(movie), 0)
        for movie in results[:k]
    ]
    ideal_grades = sorted(relevance.values(), reverse=True)[:k]
    ideal = dcg(ideal_grades)

    if ideal == 0:
        return None
    
    return dcg(actual_grades) / ideal

def average(values):
    values = [value for value in values if value is not None]
    return sum(values) / len(values) if values else None

def percentile_95(values):
    values = sorted(values)
    if not values:
        return None
    
    index = min(len(values) - 1, int(len(values) * 0.95))
    return values[index]

def format_metric(value):
    if value is None:
        return "n/a"
    
    if isinstance(value, bool):
        return "pass" if value else "fail"
    
    return f"{value:.4f}"

def summarize_reports(mode_name, reports):
    ranked_reports = [
        report
        for report in reports
        if report["no_result_correct"] is None
    ]

    no_result_reports = [
        report
        for report in reports
        if report["no_result_correct"] is not None
    ]

    return {
        "mode": mode_name,
        "cases": len(reports),
        "ranked_cases": len(ranked_reports),
        "no_result_cases": len(no_result_reports),
        "hit@5": average([
            float(report["hit@5"])
            for report in ranked_reports
        ]),
        "mrr@10": average([
            report["mrr@10"]
            for report in ranked_reports
        ]),
        "recall@10": average([
            report["recall@10"]
            for report in ranked_reports
        ]),
        "ndcg@10": average([
            report["ndcg@10"]
            for report in ranked_reports
        ]),
        "no_result_correct": average([
            float(report["no_result_correct"])
            for report in no_result_reports
        ]),
        "avg_latency_ms": average([
            report["latency_ms"]
            for report in reports
        ]),
        "p95_latency_ms": percentile_95([
            report["latency_ms"]
            for report in reports
        ]),
    }

def summarize_reports_by_intent(mode_name, reports):
    reports_by_intent = {}

    for report in reports:
        intent = report["intent"]

        if intent not in reports_by_intent:
            reports_by_intent[intent] = []

        reports_by_intent[intent].append(report)

    return {
        intent: summarize_reports(
            mode_name=mode_name,
            reports=intent_reports,
        )
        for intent, intent_reports
        in sorted(reports_by_intent.items())
    }


def print_intent_summaries(intent_summaries):
    print("intent summaries:")

    for intent, summary in intent_summaries.items():
        print(
            f" {intent}: "
            f"cases={summary['cases']}, "
            f"hit@5={format_metric(summary['hit@5'])}, "
            f"mrr@10={format_metric(summary['mrr@10'])}, "
            f"recall@10={format_metric(summary['recall@10'])}, "
            f"ndcg@10={format_metric(summary['ndcg@10'])}, "
            f"no_result={format_metric(summary['no_result_correct'])}"
        )

    print()

def evaluate_case(case, search_function, result_limit):
    relevance = relevance_by_movie_id(case)

    started_at = perf_counter()
    results = search_function(case["query"], result_limit)
    latency_ms = (perf_counter() - started_at) * 1000

    no_result_expected = len(relevance) == 0
    no_result_correct = no_result_expected and len(results) == 0

    return {
          "id": case["id"],
          "query": case["query"],
          "intent": case.get("intent", "unknown"),
          "result_ids": [result_movie_id(movie) for movie in results],
          "results": [
              {
                  "movie_id": result_movie_id(movie),
                  "title": movie["title"],
              }
              for movie in results
          ],
          "result_titles": [movie["title"] for movie in results],
          "hit@5": hit_at(results, relevance, 5),
          "mrr@10": reciprocal_rank_at(results, relevance, 10),
          "recall@10": recall_at(results, relevance, 10),
          "ndcg@10": ndcg_at(results, relevance, 10),
          "no_result_correct": no_result_correct if no_result_expected
          else None,
          "latency_ms": latency_ms,
      }

def run_mode(mode_name, cases, result_limit):
    search_function = search_modes[mode_name]
    reports = [
        evaluate_case(case, search_function, result_limit)
        for case in cases
    ]

    print(f"mode: {mode_name}")
    print()

    for report in reports:
        status = report["no_result_correct"]
        if status is None:
            status = report["hit@5"]
        print(f"[{format_metric(status)}] {report['query']}")
        print(f" intent: {report['intent']}")
        print(f" results: {' | '.join(report['result_titles']) or '<no_result>'}")
        print(
            " metrics: "
            f"hit@5={format_metric(report['hit@5'])}, "
            f"mrr@10={format_metric(report['mrr@10'])}, "
            f"recall@10={format_metric(report['recall@10'])}, "
            f"ndcg@10={format_metric(report['ndcg@10'])}, "

            f"no_result={format_metric(report['no_result_correct'])}, "
            f"latency_ms={report['latency_ms']:.1f}"
        )
        print()

    summary = summarize_reports(mode_name, reports)

    intent_summaries = summarize_reports_by_intent(
        mode_name=mode_name,
        reports=reports,
    )

    print(
        "summary: "
        f"hit@5={format_metric(summary['hit@5'])}, "
        f"mrr@10={format_metric(summary['mrr@10'])}, "
        f"recall@10={format_metric(summary['recall@10'])}, "
        f"ndcg@10={format_metric(summary['ndcg@10'])}, "
        f"no_result={format_metric(summary['no_result_correct'])}, "
        f"avg_latency_ms={format_metric(summary['avg_latency_ms'])}, "
        f"p95_latency_ms={format_metric(summary['p95_latency_ms'])}"
    )
    print_intent_summaries(intent_summaries)
    print()

    return {
        "summary": summary,
        "intent_summaries": intent_summaries,
        "reports": reports,
    }

def main():
    args = parse_args()
    cases = load_cases(args.qrels)

    mode_names = list(search_modes.keys()) if args.all else [args.mode]
    output = {
        "limit": args.limit,
        "qrels": str(args.qrels),
        "modes": {},
    }

    for mode_name in mode_names:
        output["modes"][mode_name] = run_mode(mode_name, cases,
        args.limit)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(output, indent=2),
            encoding="utf-8",
        )
        print(f"wrote: {args.json_out}")
    
if __name__ == "__main__":
    main()

