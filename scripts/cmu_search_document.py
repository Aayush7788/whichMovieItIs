from __future__ import annotations

import argparse
import csv
import gzip
import json
from collections import Counter, defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

from psycopg.types.json import Jsonb

from backend.app.db import get_connection


default_input = Path("data/processed/cmu_movies_full.jsonl")
default_character_path = Path(
    "data/raw/MovieSummaries/MovieSummaries/character.metadata.tsv"
)
default_corenlp_dir = Path(
    "data/raw/corenlp_plot_summaries/corenlp_plot_summaries"
)
maximum_corenlp_content_chars = 12000


upsert_document_sql = """
    insert into movie_search_documents (
        movie_id,
        movie_key,
        wikipedia_movie_id,
        title,
        document_type,
        source,
        source_document_id,
        content,
        metadata,
        updated_at
    )
    values (
        %(movie_id)s,
        %(movie_key)s,
        %(wikipedia_movie_id)s,
        %(title)s,
        %(document_type)s,
        %(source)s,
        %(source_document_id)s,
        %(content)s,
        %(metadata)s,
        now()
    )
    on conflict (source, document_type, source_document_id)
    do update set
        movie_id = excluded.movie_id,
        movie_key = excluded.movie_key,
        wikipedia_movie_id = excluded.wikipedia_movie_id,
        title = excluded.title,
        content = excluded.content,
        metadata = excluded.metadata,
        updated_at = now();
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=default_input)
    parser.add_argument("--character-path", type=Path, default=default_character_path)
    parser.add_argument("--corenlp-dir", type=Path, default=default_corenlp_dir)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--commit-interval", type=int, default=500)
    parser.add_argument("--skip-characters", action="store_true")
    parser.add_argument("--skip-corenlp", action="store_true")
    return parser.parse_args()


def clean_text(value: object) -> str:
    return " ".join(str(value or "").split())


def read_movie_records(path: Path, limit: int) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if not line.strip():
                continue

            records.append(json.loads(line))

            if limit > 0 and len(records) >= limit:
                break

    return records


def fetch_movie_lookup(cursor) -> dict[str, dict[str, object]]:
    cursor.execute(
        """
        select id, movie_key, wikipedia_movie_id, title
        from movies;
        """
    )

    return {
        str(wikipedia_movie_id): {
            "movie_id": movie_id,
            "movie_key": movie_key,
            "title": title,
        }
        for movie_id, movie_key, wikipedia_movie_id, title in cursor.fetchall()
    }


def read_character_documents(
    path: Path,
    allowed_movie_ids: set[str],
    titles_by_movie_id: dict[str, str],
) -> dict[str, dict[str, object]]:
    grouped_rows: dict[str, list[str]] = defaultdict(list)

    if not path.exists():
        return {}

    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter="\t")

        for row in reader:
            if len(row) != 13:
                continue

            wikipedia_movie_id = row[0]

            if wikipedia_movie_id not in allowed_movie_ids:
                continue

            character_name = clean_text(row[3])
            actor_name = clean_text(row[8])

            if character_name and actor_name:
                grouped_rows[wikipedia_movie_id].append(
                    f"{character_name} played by {actor_name}"
                )
            elif character_name:
                grouped_rows[wikipedia_movie_id].append(
                    f"character {character_name}"
                )
            elif actor_name:
                grouped_rows[wikipedia_movie_id].append(
                    f"cast member {actor_name}"
                )

    documents: dict[str, dict[str, object]] = {}

    for wikipedia_movie_id, rows in grouped_rows.items():
        unique_rows = list(dict.fromkeys(rows))
        title = titles_by_movie_id.get(wikipedia_movie_id, "")

        documents[wikipedia_movie_id] = {
            "document_type": "character_cast",
            "source": "cmu_character_metadata",
            "source_document_id": f"{wikipedia_movie_id}:character_cast",
            "content": (
                f"Characters and cast in {title}: "
                + ". ".join(unique_rows[:120])
            ),
            "metadata": {
                "character_cast_count": len(unique_rows),
            },
        }

    return documents


def join_tokens(words: list[str]) -> str:
    no_space_before = {
        ".",
        ",",
        ";",
        ":",
        "?",
        "!",
        ")",
        "]",
        "}",
        "'s",
        "n't",
    }
    no_space_after = {"(", "[", "{"}

    output = ""

    for word in words:
        if not output:
            output = word
        elif word in no_space_before:
            output += word
        elif output[-1] in no_space_after:
            output += word
        else:
            output += " " + word

    return output


def iter_sentence_tokens(root: ET.Element):
    sentences = root.find("./document/sentences")

    if sentences is None:
        return

    for sentence in sentences.findall("sentence"):
        tokens_node = sentence.find("tokens")

        if tokens_node is None:
            continue

        tokens = []

        for token in tokens_node.findall("token"):
            word = clean_text(token.findtext("word"))
            lemma = clean_text(token.findtext("lemma") or word)
            pos = clean_text(token.findtext("POS"))
            ner = clean_text(token.findtext("NER") or "O")

            if not word:
                continue

            tokens.append(
                {
                    "word": word,
                    "lemma": lemma,
                    "pos": pos,
                    "ner": ner,
                }
            )

        if tokens:
            yield tokens


def extract_named_entities(tokens: list[dict[str, str]]) -> list[str]:
    entities: list[str] = []
    current_words: list[str] = []
    current_type = "O"

    def flush_current() -> None:
        if current_words:
            entities.append(join_tokens(current_words))

    for token in tokens:
        ner = token["ner"]

        if ner == "O":
            flush_current()
            current_words = []
            current_type = "O"
            continue

        if ner != current_type:
            flush_current()
            current_words = [token["word"]]
            current_type = ner
        else:
            current_words.append(token["word"])

    flush_current()

    return entities


def extract_coreference_chains(
    root: ET.Element,
    maximum_chains: int = 40,
) -> list[str]:
    coreference = root.find("./document/coreference")

    if coreference is None:
        return []

    chains: list[str] = []

    for chain in coreference.findall("coreference"):
        mentions = []

        for mention in chain.findall("mention"):
            text = clean_text(mention.findtext("text"))

            if text:
                mentions.append(text)

        unique_mentions = list(dict.fromkeys(mentions))

        if len(unique_mentions) > 1:
            chains.append(" / ".join(unique_mentions[:8]))

        if len(chains) >= maximum_chains:
            break

    return chains


def parse_corenlp_document(
    path: Path,
    title: str,
) -> dict[str, object] | None:
    try:
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as file:
            root = ET.parse(file).getroot()
    except (OSError, ET.ParseError):
        return None

    entity_counter: Counter[str] = Counter()
    action_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    sentence_texts: list[str] = []

    for tokens in iter_sentence_tokens(root):
        words = [token["word"] for token in tokens]
        sentence_texts.append(join_tokens(words))

        for entity in extract_named_entities(tokens):
            entity_counter[entity] += 1

        for token in tokens:
            lemma = token["lemma"].casefold()
            pos = token["pos"]

            if len(lemma) <= 2:
                continue

            if pos.startswith("VB"):
                action_counter[lemma] += 1
            elif pos.startswith(("NN", "JJ")):
                keyword_counter[lemma] += 1

    coreference_chains = extract_coreference_chains(root)

    sections = [f"CoreNLP plot signals for {title}."]

    if entity_counter:
        sections.append(
            "Named entities: "
            + ", ".join(
                entity
                for entity, _count
                in entity_counter.most_common(80)
            )
            + "."
        )

    if action_counter:
        sections.append(
            "Actions: "
            + ", ".join(
                action
                for action, _count
                in action_counter.most_common(120)
            )
            + "."
        )

    if keyword_counter:
        sections.append(
            "Important plot words: "
            + ", ".join(
                keyword
                for keyword, _count
                in keyword_counter.most_common(160)
            )
            + "."
        )

    if coreference_chains:
        sections.append(
            "Coreference chains: "
            + ". ".join(coreference_chains)
            + "."
        )

    if sentence_texts:
        sections.append(
            "Plot sentences: "
            + " ".join(sentence_texts[:100])
        )

    content = " ".join(sections)

    return {
        "document_type": "corenlp_plot_signals",
        "source": "cmu_corenlp_plot_summaries",
        "source_document_id": f"{path.stem.removesuffix('.xml')}:corenlp_plot_signals",
        "content": content[:maximum_corenlp_content_chars],
        "metadata": {
            "entity_count": len(entity_counter),
            "action_count": len(action_counter),
            "keyword_count": len(keyword_counter),
            "coreference_chain_count": len(coreference_chains),
        },
    }


def build_plot_document(record: dict[str, object]) -> dict[str, object]:
    wikipedia_movie_id = str(record["wikipedia_movie_id"])

    return {
        "document_type": "plot_summary",
        "source": "cmu_movie_summary_corpus",
        "source_document_id": f"{wikipedia_movie_id}:plot_summary",
        "content": clean_text(record["plot_summary"]),
        "metadata": {
            "genres": record.get("genres") or [],
            "release_date": record.get("release_date"),
        },
    }


def upsert_document(
    cursor,
    movie: dict[str, object],
    wikipedia_movie_id: str,
    title: str,
    document: dict[str, object],
) -> None:
    cursor.execute(
        upsert_document_sql,
        {
            "movie_id": movie["movie_id"],
            "movie_key": movie["movie_key"],
            "wikipedia_movie_id": wikipedia_movie_id,
            "title": title,
            "document_type": document["document_type"],
            "source": document["source"],
            "source_document_id": document["source_document_id"],
            "content": document["content"],
            "metadata": Jsonb(document["metadata"]),
        },
    )


def main() -> None:
    args = parse_args()

    if args.limit < 0:
        raise ValueError("limit must be zero or greater")

    if args.commit_interval < 1:
        raise ValueError("commit interval must be at least one")

    records = read_movie_records(args.input, args.limit)
    allowed_movie_ids = {
        str(record["wikipedia_movie_id"])
        for record in records
    }
    titles_by_movie_id = {
        str(record["wikipedia_movie_id"]): clean_text(record["title"])
        for record in records
    }

    character_documents = {}

    if not args.skip_characters:
        character_documents = read_character_documents(
            path=args.character_path,
            allowed_movie_ids=allowed_movie_ids,
            titles_by_movie_id=titles_by_movie_id,
        )

    statistics = Counter()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            movie_lookup = fetch_movie_lookup(cursor)

            for record in records:
                wikipedia_movie_id = str(record["wikipedia_movie_id"])
                movie = movie_lookup.get(wikipedia_movie_id)

                if movie is None:
                    statistics["missing_movie"] += 1
                    continue

                title = clean_text(record.get("title") or movie["title"])

                upsert_document(
                    cursor=cursor,
                    movie=movie,
                    wikipedia_movie_id=wikipedia_movie_id,
                    title=title,
                    document=build_plot_document(record),
                )
                statistics["plot_summary"] += 1

                character_document = character_documents.get(
                    wikipedia_movie_id
                )

                if character_document is not None:
                    upsert_document(
                        cursor=cursor,
                        movie=movie,
                        wikipedia_movie_id=wikipedia_movie_id,
                        title=title,
                        document=character_document,
                    )
                    statistics["character_cast"] += 1

                if not args.skip_corenlp:
                    corenlp_path = (
                        args.corenlp_dir
                        / f"{wikipedia_movie_id}.xml.gz"
                    )

                    if corenlp_path.exists():
                        corenlp_document = parse_corenlp_document(
                            path=corenlp_path,
                            title=title,
                        )

                        if corenlp_document is not None:
                            upsert_document(
                                cursor=cursor,
                                movie=movie,
                                wikipedia_movie_id=wikipedia_movie_id,
                                title=title,
                                document=corenlp_document,
                            )
                            statistics["corenlp_plot_signals"] += 1
                        else:
                            statistics["corenlp_parse_error"] += 1
                    else:
                        statistics["corenlp_missing"] += 1

                statistics["movies_processed"] += 1

                if (
                    statistics["movies_processed"]
                    % args.commit_interval
                    == 0
                ):
                    connection.commit()
                    print(
                        "processed movies: "
                        f"{statistics['movies_processed']}"
                    )

            connection.commit()

    print("search document build complete")

    for name, value in sorted(statistics.items()):
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()
