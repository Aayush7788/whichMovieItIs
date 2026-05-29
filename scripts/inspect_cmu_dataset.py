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

def inspect_movie_metadata(path:Path) -> tuple[set[str], dict[str, object]]:
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
    
    report = {
        "rows": sum(columns_counts.values()), 
        "unique_wikipedia_ids": len(wikipedia_ids), 
        "column_counts": dict(columns_counts), 
        "missing_fields": dict(missing_fields),
    }

    return wikipedia_ids, report

def inspect_plot_summaries(path: Path) -> tuple[set[str], dict[str, int]]:
    wikipedia_ids = set()
    rows = 0
    bad_rows = 0
    duplicate_ids = 0

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            rows += 1
            parts = line.rstrip("\n").split("\t", 1)
        
            if len(parts) != 2:
                bad_rows += 1
                continue

            wikipedia_id = parts[0]

            if wikipedia_id in wikipedia_ids:
                duplicate_ids += 1
                continue

            wikipedia_ids.add(wikipedia_id)

    report = {
        "rows": rows, 
        "unique_wikipedia_ids": len(wikipedia_ids),
        "bad_rows": bad_rows, 
        "duplicate_wikipedia_ids": duplicate_ids,
    }

    return wikipedia_ids, report

def main() -> None:
    required_files = [movie_metadata_path, plot_summaries_path]

    for path in required_files:
        if not path.exists():
            raise SystemExit(f"missing required file:{path}")

    metadata_ids, metadata_report = inspect_movie_metadata(movie_metadata_path)
    plot_ids, plot_report = inspect_plot_summaries(plot_summaries_path)

    joined_ids = metadata_ids & plot_ids
    plot_without_metadata = plot_ids - metadata_ids
    metadata_without_plot = metadata_ids - plot_ids

    print("cmu dataset files found")
    print(f"movie metadata rows:{count_lines(movie_metadata_path)}")
    print(f"plot summary rows: {count_lines(plot_summaries_path)}")
    print(f"coreNlp files:{count_corenlp_files(coreNlp_dir)}")
    print()
    print("movie metadata inspection")
    print(metadata_report)
    print()
    print("plot summary inspection")
    print(plot_report)
    print()
    print("join inspection")
    print(f"joined ids: {len(joined_ids)}")
    print(f"plot ids without metadata: {len(plot_without_metadata)}")
    print(f"metadata ids without plot: {len(metadata_without_plot)}")
    print(f"first unmatched plot ids: {sorted(plot_without_metadata)[:10]}")

if __name__== "__main__":
    main()
    