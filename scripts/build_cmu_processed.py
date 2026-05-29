from __future__ import annotations
import ast
import csv
import argparse
from pathlib import Path

Raw_dir = Path("data/raw/MovieSummaries/MovieSummaries")
default_output = Path("data/processed/cmu_movies_sample.jsonl")

movie_metadata_columns = [
    "wikipedia_movie_id", 
    "freebase_movie_id", 
    "title", 
    "release_date",
    "box_office_revenue",
    "runtime", 
    "language", 
    "countries", 
    "genres",
]

def parse_map_values(value: str) -> list[str]:
    if value == "":
        return []

    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []
    
    if not isinstance(parsed, dict):
        return []

    return [str(item) for item in parsed.values()]

def parse_float(value: str) -> float | None:
    if value == "":
        return None
    
    try: 
        return float(value)
    except ValueError:
        return None
    
def read_movie_metadata(path: Path) -> dict[str, dict[str, object]]:
    movies = {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t")

        for row in reader:
            if len(row) != len(movie_metadata_columns):
                continue
            wikipedia_movie_id = row[0]

            movies[wikipedia_movie_id] = {
                "wikipedia_movie_id": wikipedia_movie_id, 
                "freebase_movie_id": row[1], 
                "title": row[2], 
                "release_date": row[3] or None, 
                "box_office_revenue": parse_float(row[4]),
                "runtime": parse_float(row[5]),
                "languages": parse_map_values(row[6]),
                "countries": parse_map_values(row[7]),
                "genres": parse_map_values(row[8]),
            }
    return movies

def read_plot_summaries(path: Path) ->dict[str, str]:
    plots = {}

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            parts = line.rstrip("\n").split("\t", 1)

            if len(parts) != 2:
                continue

            wikipedia_movie_id, plot_summary = parts
            plots[wikipedia_movie_id] = plot_summary
        
    return plots


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()

    metadata_path = Raw_dir / "movie.metadata.tsv"
    plot_path = Raw_dir / "plot_summaries.txt"
    
    movies = read_movie_metadata(metadata_path)
    print(f"metadata records loaded: {len(movies)}")
    plots = read_plot_summaries(plot_path)
    joined_ids = set(movies) & set(plots)
   

    print(f"metadata path exits: {metadata_path.exists()}")
    print(f"plot path exits: {plot_path.exists()}")
    print(f"limit: {args.limit}")
    print(f"output: {args.output}")
    print()
    print(f"metadata records loaded: {len(movies)}")
    print(f"plot record loaded: {len(plots)}")
    print(f"joined records: {len(joined_ids)}")

if __name__ == "__main__":
    main()