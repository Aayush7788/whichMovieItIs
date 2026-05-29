from pathlib import Path

Raw_dir = Path("data/raw/MovieSummaries/MovieSummaries")
coreNlp_dir = Path("data/raw/corenlp_plot_summaries/corenlp_plot_summaries")

movie_metadata_path = Raw_dir / "movie.metadata.tsv"
plot_summaries_path = Raw_dir / "plot_summaries.txt"

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

def main() -> None:
    required_files = [movie_metadata_path, plot_summaries_path]

    for path in required_files:
        if not path.exists():
            raise SystemExit(f"missing required file:{path}")

    print("cmu dataset files found")
    print(f"movie metadata rows:{count_lines(movie_metadata_path)}")
    print(f"plot summary rows: {count_lines(plot_summaries_path)}")
    print(f"coreNlp files:{count_corenlp_files(coreNlp_dir)}")

if __name__== "__main__":
    main()
    