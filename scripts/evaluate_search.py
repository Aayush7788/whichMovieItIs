import json
from pathlib import Path
import argparse
from backend.app.services.hybrid_search import search_movies_hybrid
from backend.app.services.vector_search import search_movies_by_embedding
from backend.app.services.search import search_movies

eval_file = Path("data/evaluation/search_queries.jsonl")
limit = 5

search_modes = {
    "full-text": search_movies,
    "vector": search_movies_by_embedding,
    "hybrid": search_movies_hybrid,
}

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=search_modes.keys(), default="full-text")
    return parser.parse_args()

def load_cases():
    cases = []

    with eval_file.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            case  = json.loads(line)

            if "query" not in case or "expected_any" not in case:
                raise ValueError(
                    f"{eval_file}:{line_number} must include query and expected_any"
                )
            
            cases.append(case)
    
    return cases

def evaluate_case(case, search_function):
    query = case["query"]
    expected_any = case["expected_any"]
    must_find = case.get("must_find", bool(expected_any))

    results = search_function(query, limit)
    titles = [movie["title"] for movie in results]
    expected_titles = set(expected_any)

    if must_find:
        passed = any(title in expected_titles for title in titles)
        top_1_hit = bool(titles) and titles[0] in expected_titles
    else:
        passed = len(titles) == 0
        top_1_hit = passed

    return {
        "query": query, 
        "expected_any": expected_any, 
        "titles": titles,
        "must_find": must_find,
        "passed": passed, 
        "top_1_hit": top_1_hit,
    }

def main():
    args = parse_args()
    search_function = search_modes[args.mode]

    print(f"mode: {args.mode}")
    print()

    reports = [evaluate_case(case, search_function) for case in load_cases()]

    for report in reports:
        status = "pass" if report["passed"] else "fail"
        expected = ", ".join(report["expected_any"]) or "<no_result>"
        got = " | ".join(report["titles"]) or "<no_result>"

        print(f"[{status}] {report['query']}")
        print(f" expected: {expected}")
        print(f" got: {got}")
    
    passed_count = sum(1 for report in reports if report["passed"])
    positive_reports = [report for report in reports if report["must_find"]]
    top_1_hits = sum(1 for report in positive_reports if report["top_1_hit"])

    print()
    print(f"summary: {passed_count}/{len(reports)} cases passed")
    print(f"top_1_hit {top_1_hits}/{len(positive_reports)} positive_reports")

    if passed_count != len(reports):
        raise SystemExit(1)
    
if __name__ == "__main__":
    main()

