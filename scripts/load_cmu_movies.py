import json 
from pathlib import Path
from backend.app.db import get_connection
from psycopg.types.json import Jsonb

default_input = Path("data/processed/cmu_movies_sample.jsonl")

insert_movie_sql = """
    insert into movies (
        wikipedia_movie_id, 
        freebase_movie_id, 
        title, 
        release_date,
        box_office_revenue, 
        runtime,
        languages, 
        countries,
        genres,
        plot_summary,
        source
    ) 
    values (
        %(wikipedia_movie_id)s,
        %(freebase_movie_id)s,
        %(title)s,
        %(release_date)s,
        %(box_office_revenue)s,
        %(runtime)s,
        %(languages)s,
        %(countries)s,
        %(genres)s,
        %(plot_summary)s,
        %(source)s
    )
    on conflict (wikipedia_movie_id) do update set
        freebase_movie_id = excluded.freebase_movie_id, 
        title = excluded.title,
        release_date = excluded.release_date,
        box_office_revenue = excluded.box_office_revenue,
        runtime = excluded.runtime,
        languages = excluded.languages, 
        countries = excluded.countries,
        genres = excluded.genres,
        plot_summary = excluded.plot_summary,
        source = excluded.source;
"""

def read_json(path: Path) -> list[dict[str, object]]:
    records = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            if line.strip():
                records.append(json.loads(line))

    return records

def main() -> None:
    records = read_json(default_input)

    with get_connection() as conn:
        with conn.cursor() as cur:
            for record in records:
                db_record = record.copy()
                db_record["languages"] = Jsonb(db_record["languages"])
                db_record["countries"] = Jsonb(db_record["countries"])
                db_record["genres"] = Jsonb(db_record["genres"])
                cur.execute(insert_movie_sql, db_record)
        conn.commit()
    print(f"movies loaded: {len(records)}")

if __name__ == "__main__":
    main()