import argparse
import json
from collections import Counter
from pathlib import Path

import psycopg

from backend.app.db import get_connection

default_qrels_path = Path(
    "data/evaluation/search_qrels.jsonl"
)

allowed_intents = {
    "exact_title",
    "franchise_title",
    "object_scene",
    "semantic_plot",
    "no_result",
    "dialogue_memory",
    "character_memory",
}


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--qrels",
        type=Path,
        default=default_qrels_path,
    )
    parser.add_argument(
        "--minimum-cases",
        type=int,
        default=1,
    )

    return parser.parse_args()


def load_json_lines(path):
    cases = []
    errors = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(
            file,
            start=1,
        ):
            line = line.strip()

            if not line:
                continue

            try:
                case = json.loads(line)
            except json.JSONDecodeError as error:
                errors.append(
                    (
                        f"{path}:{line_number}: "
                        f"invalid JSON: {error.msg}"
                    )
                )
                continue

            cases.append((line_number, case))

    return cases, errors


def validate_cases(path, cases, minimum_cases):
    errors = []
    case_ids = {}
    queries = {}
    movie_references = {}

    intent_counts = Counter()
    grade_counts = Counter()

    if len(cases) < minimum_cases:
        errors.append(
            (
                f"{path}: expected at least "
                f"{minimum_cases} cases, found {len(cases)}"
            )
        )

    for line_number, case in cases:
        if not isinstance(case, dict):
            errors.append(
                f"{path}:{line_number}: case must be an object"
            )
            continue

        required_fields = {
            "id",
            "query",
            "intent",
            "relevant",
        }

        missing_fields = required_fields - set(case)

        if missing_fields:
            errors.append(
                (
                    f"{path}:{line_number}: missing fields "
                    f"{sorted(missing_fields)}"
                )
            )
            continue

        case_id = case["id"]
        query = case["query"]
        intent = case["intent"]
        relevant = case["relevant"]

        if not isinstance(case_id, str) or not case_id.strip():
            errors.append(
                f"{path}:{line_number}: id must be non-empty"
            )
        elif case_id in case_ids:
            errors.append(
                (
                    f"{path}:{line_number}: duplicate id "
                    f"{case_id!r}; first used on line "
                    f"{case_ids[case_id]}"
                )
            )
        else:
            case_ids[case_id] = line_number

        if not isinstance(query, str) or not query.strip():
            errors.append(
                f"{path}:{line_number}: query must be non-empty"
            )
        else:
            normalized_query = query.strip().casefold()

            if normalized_query in queries:
                errors.append(
                    (
                        f"{path}:{line_number}: duplicate query "
                        f"{query!r}; first used on line "
                        f"{queries[normalized_query]}"
                    )
                )
            else:
                queries[normalized_query] = line_number

        if intent not in allowed_intents:
            errors.append(
                (
                    f"{path}:{line_number}: unknown intent "
                    f"{intent!r}"
                )
            )
        else:
            intent_counts[intent] += 1

        if not isinstance(relevant, list):
            errors.append(
                (
                    f"{path}:{line_number}: relevant "
                    f"must be a list"
                )
            )
            continue

        if intent == "no_result" and relevant:
            errors.append(
                (
                    f"{path}:{line_number}: no_result "
                    f"case must have an empty relevant list"
                )
            )

        if intent != "no_result" and not relevant:
            errors.append(
                (
                    f"{path}:{line_number}: {intent} "
                    f"case must include a relevant movie"
                )
            )

        case_movie_ids = set()

        for item_number, item in enumerate(
            relevant,
            start=1,
        ):
            if not isinstance(item, dict):
                errors.append(
                    (
                        f"{path}:{line_number}: relevant "
                        f"item {item_number} must be an object"
                    )
                )
                continue

            required_movie_fields = {
                "movie_id",
                "title",
                "grade",
            }

            missing_movie_fields = (
                required_movie_fields - set(item)
            )

            if missing_movie_fields:
                errors.append(
                    (
                        f"{path}:{line_number}: relevant "
                        f"item {item_number} missing fields "
                        f"{sorted(missing_movie_fields)}"
                    )
                )
                continue

            movie_id = item["movie_id"]
            title = item["title"]
            grade = item["grade"]

            if (
                not isinstance(movie_id, str)
                or not movie_id.strip()
            ):
                errors.append(
                    (
                        f"{path}:{line_number}: relevant "
                        f"item {item_number} has invalid movie_id"
                    )
                )
                continue

            if movie_id in case_movie_ids:
                errors.append(
                    (
                        f"{path}:{line_number}: movie ID "
                        f"{movie_id!r} appears more than once"
                    )
                )
            else:
                case_movie_ids.add(movie_id)

            if not isinstance(title, str) or not title.strip():
                errors.append(
                    (
                        f"{path}:{line_number}: relevant "
                        f"item {item_number} has invalid title"
                    )
                )
                continue

            if not isinstance(grade, int) or grade not in {
                1,
                2,
                3,
            }:
                errors.append(
                    (
                        f"{path}:{line_number}: relevant "
                        f"item {item_number} has invalid grade "
                        f"{grade!r}; expected 1, 2, or 3"
                    )
                )
                continue

            grade_counts[grade] += 1

            if movie_id not in movie_references:
                movie_references[movie_id] = []

            movie_references[movie_id].append(
                {
                    "line_number": line_number,
                    "title": title,
                }
            )

    return {
        "errors": errors,
        "movie_references": movie_references,
        "intent_counts": intent_counts,
        "grade_counts": grade_counts,
    }


def validate_database_movies(
    path,
    movie_references,
):
    errors = []

    if not movie_references:
        return errors

    movie_ids = sorted(movie_references)

    try:
        with get_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT wikipedia_movie_id, title
                    FROM movies
                    WHERE wikipedia_movie_id = ANY(%s);
                    """,
                    (movie_ids,),
                )

                database_movies = {
                    str(movie_id): title
                    for movie_id, title
                    in cursor.fetchall()
                }
    except psycopg.Error as error:
        return [
            f"database validation failed: {error}"
        ]

    missing_movie_ids = (
        set(movie_ids) - set(database_movies)
    )

    for movie_id in sorted(missing_movie_ids):
        references = movie_references[movie_id]
        line_numbers = sorted({
            reference["line_number"]
            for reference in references
        })

        errors.append(
            (
                f"{path}: movie ID {movie_id!r} "
                f"does not exist; used on lines "
                f"{line_numbers}"
            )
        )

    for movie_id, references in movie_references.items():
        actual_title = database_movies.get(movie_id)

        if actual_title is None:
            continue

        for reference in references:
            expected_title = reference["title"]

            if expected_title != actual_title:
                errors.append(
                    (
                        f"{path}:{reference['line_number']}: "
                        f"movie ID {movie_id!r} title mismatch; "
                        f"qrel has {expected_title!r}, "
                        f"database has {actual_title!r}"
                    )
                )

    return errors


def print_coverage(
    case_count,
    intent_counts,
    grade_counts,
):
    print(f"cases: {case_count}")
    print("intents:")

    for intent in sorted(intent_counts):
        print(
            f"  {intent}: {intent_counts[intent]}"
        )

    print("grades:")

    for grade in sorted(grade_counts):
        print(
            f"  grade {grade}: {grade_counts[grade]}"
        )


def main():
    args = parse_args()

    cases, load_errors = load_json_lines(
        args.qrels
    )

    validation = validate_cases(
        path=args.qrels,
        cases=cases,
        minimum_cases=args.minimum_cases,
    )

    errors = [
        *load_errors,
        *validation["errors"],
    ]

    errors.extend(
        validate_database_movies(
            path=args.qrels,
            movie_references=validation[
                "movie_references"
            ],
        )
    )

    print_coverage(
        case_count=len(cases),
        intent_counts=validation[
            "intent_counts"
        ],
        grade_counts=validation[
            "grade_counts"
        ],
    )

    if errors:
        print()
        print("validation failed:")

        for error in errors:
            print(f"- {error}")

        return 1

    print()
    print("qrels validation passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())