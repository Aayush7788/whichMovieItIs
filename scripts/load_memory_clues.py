from __future__ import annotations
from collections import Counter
from backend.app.db import get_connection

source_name = "curated_memory_clues_v1"

memory_clues = [
    {
        "wikipedia_movie_id": "52371",
        "clue_type": "plot_memory",
        "clue_text": "ship hits iceberg titanic sinking ocean liner",
    },
    {
        "wikipedia_movie_id": "6524086",
        "clue_type": "plot_memory",
        "clue_text": "ship hits iceberg titanic sinking a night to remember ocean liner",
    },
    {
        "wikipedia_movie_id": "30007",
        "clue_type": "iconic_object",
        "clue_text": "red pill blue pill neo morpheus simulated reality matrix",
    },
    {
        "wikipedia_movie_id": "44501",
        "clue_type": "plot_memory",
        "clue_text": "man stranded island volleyball wilson plane crash cast away",
    },
    {
        "wikipedia_movie_id": "239587",
        "clue_type": "plot_memory",
        "clue_text": "fish father searches ocean son clownfish nemo marlin",
    },
    {
        "wikipedia_movie_id": "11659396",
        "clue_type": "plot_memory",
        "clue_text": "old man flying house balloons up",
    },
    {
        "wikipedia_movie_id": "2750041",
        "clue_type": "plot_memory",
        "clue_text": "man tattoos clues memory loss short term memory memento",
    },
    {
        "wikipedia_movie_id": "88678",
        "clue_type": "plot_memory",
        "clue_text": "young lion avenges father uncle scar simba lion king",
    },
    {
        "wikipedia_movie_id": "73441",
        "clue_type": "plot_memory",
        "clue_text": "alien child bicycle moon phone home et extra terrestrial",
    },
    {
        "wikipedia_movie_id": "52549",
        "clue_type": "quote",
        "clue_text": "may the force be with you star wars jedi luke skywalker darth vader",
    },
    {
        "wikipedia_movie_id": "53964",
        "clue_type": "quote",
        "clue_text": "may the force be with you star wars empire strikes back jedi darth vader",
    },
    {
        "wikipedia_movie_id": "50744",
        "clue_type": "quote",
        "clue_text": "may the force be with you star wars return of the jedi luke vader",
    },
    {
        "wikipedia_movie_id": "50793",
        "clue_type": "franchise_alias",
        "clue_text": "star wars phantom menace jedi force lightsaber",
    },
    {
        "wikipedia_movie_id": "50957",
        "clue_type": "franchise_alias",
        "clue_text": "star wars attack of the clones jedi force lightsaber",
    },
    {
        "wikipedia_movie_id": "55447",
        "clue_type": "franchise_alias",
        "clue_text": "star wars revenge of the sith jedi force lightsaber",
    },
    {
        "wikipedia_movie_id": "30327",
        "clue_type": "quote",
        "clue_text": "ill be back terminator cyborg robot arnold",
    },
    {
        "wikipedia_movie_id": "34344124",
        "clue_type": "quote",
        "clue_text": "ill be back terminator 2 judgment day cyborg robot arnold",
    },
    {
        "wikipedia_movie_id": "20691749",
        "clue_type": "quote",
        "clue_text": "you cant handle the truth courtroom military lawyer a few good men",
    },
    {
        "wikipedia_movie_id": "41528",
        "clue_type": "quote",
        "clue_text": "life is like a box of chocolates forrest gump",
    },
    {
        "wikipedia_movie_id": "54166",
        "clue_type": "character_memory",
        "clue_text": "archaeologist whip fedora indiana jones raiders lost ark",
    },
    {
        "wikipedia_movie_id": "51888",
        "clue_type": "character_memory",
        "clue_text": "archaeologist whip fedora indiana jones last crusade",
    },
    {
        "wikipedia_movie_id": "81503",
        "clue_type": "character_memory",
        "clue_text": "archaeologist whip fedora indiana jones temple of doom",
    },
    {
        "wikipedia_movie_id": "4276475",
        "clue_type": "character_memory",
        "clue_text": "masked vigilante gotham billionaire batman joker dark knight",
    },
    {
        "wikipedia_movie_id": "481605",
        "clue_type": "character_memory",
        "clue_text": "masked vigilante gotham billionaire batman begins bruce wayne",
    },
    {
        "wikipedia_movie_id": "4726",
        "clue_type": "character_memory",
        "clue_text": "masked vigilante gotham billionaire batman bruce wayne",
    },
    {
        "wikipedia_movie_id": "30006",
        "clue_type": "character_memory",
        "clue_text": "serial killer chianti fava beans hannibal lecter silence of the lambs",
    },
]


fetch_movies_sql = """
    select id, wikipedia_movie_id, title
    from movies
    where wikipedia_movie_id = any(%(movie_ids)s::text[]);
"""


upsert_clue_sql = """
    insert into movie_memory_clues (
        movie_id,
        wikipedia_movie_id,
        clue_type,
        source,
        clue_text,
        updated_at
    )
    values (
        %(movie_id)s,
        %(wikipedia_movie_id)s,
        %(clue_type)s,
        %(source)s,
        %(clue_text)s,
        now()
    )
    on conflict (
        wikipedia_movie_id,
        clue_type,
        source,
        clue_text
    )
    do update set
        movie_id = excluded.movie_id,
        updated_at = now();
"""


def main() -> None:
    movie_ids = sorted({
        clue["wikipedia_movie_id"]
        for clue in memory_clues
    })

    statistics = Counter()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                fetch_movies_sql,
                {"movie_ids": movie_ids},
            )

            movies = {
                str(wikipedia_movie_id): {
                    "movie_id": movie_id,
                    "title": title,
                }
                for movie_id, wikipedia_movie_id, title
                in cursor.fetchall()
            }

            for clue in memory_clues:
                wikipedia_movie_id = clue["wikipedia_movie_id"]
                movie = movies.get(wikipedia_movie_id)

                if movie is None:
                    statistics["missing_movie"] += 1
                    print(
                        "missing movie: "
                        f"{wikipedia_movie_id} "
                        f"{clue['clue_text']}"
                    )
                    continue

                cursor.execute(
                    upsert_clue_sql,
                    {
                        "movie_id": movie["movie_id"],
                        "wikipedia_movie_id": wikipedia_movie_id,
                        "clue_type": clue["clue_type"],
                        "source": source_name,
                        "clue_text": clue["clue_text"],
                    },
                )
                statistics["loaded"] += 1

            connection.commit()

    print("memory clues loaded")

    for name, value in sorted(statistics.items()):
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()