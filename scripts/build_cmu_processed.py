from __future__ import annotations

import argparse
from pathlib import Path

Raw_dir = Path("data/raw/MovieSummaries/MovieSummaries")
default_output = Path("data/processed/cmu_movies_sample.jsonl")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--output", type=Path, default=default_output)
    args = parser.parse_args()

    metadata_path = Raw_dir / "movie.metadata.tsv"
    plot_path = Raw_dir / "plot_summaries.txt"

    print(f"metadata path exits: {metadata_path.exists()}")
    print(f"plot path exits: {plot_path.exists()}")
    print(f"limit: {args.limit}")
    print(f"output: {args.output}")

if __name__ == "__main__":
    main()