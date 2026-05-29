from pathlib import Path
from collections import Counter
import csv


Raw_dir = Path("data/raw/MovieSummaries/MovieSummaries")
coreNlp_dir = Path("data/raw/corenlp_plot_summaries/corenlp_plot_summaries")

movie_metadata_path = Raw_dir / "movie.metadata.tsv"
plot_summaries_path = Raw_dir / "plot_summaries.txt"

movie_metadata_columns = [
    "wikipedia_movie_id",
    "freebase_movie_id",
    "title",
    "release_date",
    "box_office_revenue",
    "runtime",
    "language",
    "countries",
    "genres"
]

def count_lines(path: Path) -> int:
    count = 0
    with path.open("rb") as file:
        for _ in file:
            count += 1
    return count


def count_corenlp_files(path: Path)->int:
    if not path.exists():
        return 0
    return sum(1 for _ in path.glob("*.xml.gz"))

def inspect_movie_metadata(path:Path) -> dict[str, object]:
    wikipedia_ids = set()
    columns_counts = Counter()
    missing_fields =  Counter()

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t")

        for row in reader:
            columns_counts[len(row)] += 1

            if len(row) != len(movie_metadata_columns):
                continue

            wikipedia_ids.add(row[0])

            for column_name, value in zip(movie_metadata_columns, row):
                if value == "":
                    missing_fields[column_name] += 1
    
    return{
        "rows": sum(columns_counts.values()), 
        "unique_wikipedia_ids": len(wikipedia_ids), 
        "column_counts": dict(columns_counts), 
        "missing_fields": dict(missing_fields),
    }

def main() -> None:
    required_files = [movie_metadata_path, plot_summaries_path]

    for path in required_files:
        if not path.exists():
            raise SystemExit(f"missing required file:{path}")

    metadata_report = inspect_movie_metadata(movie_metadata_path)

    print("cmu dataset files found")
    print(f"movie metadata rows:{count_lines(movie_metadata_path)}")
    print(f"plot summary rows: {count_lines(plot_summaries_path)}")
    print(f"coreNlp files:{count_corenlp_files(coreNlp_dir)}")
    print()
    print("movie metadata inspection")
    print(metadata_report)

if __name__== "__main__":
    main()
    