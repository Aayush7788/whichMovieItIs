## 25/5/26 
created the folder and files structure
setup git
and all setup of fastapi backend, react frontend and postgresql with pgvector database 


## 26/5/26
implemented backend health endpoint, for fastapi
and database health endpoint with pydantic, psycopg

learn the database connetion in postgresql with docker with fastapi

## 28-29/5/26
output in cmu inspection, 

movie metadata rows:81741
plot summary rows: 42306
coreNlp files:42306

movie metadata inspection
{'rows': 81741, 'unique_wikipedia_ids': 81741, 'column_counts': {9: 81741}, 'missing_fields': {'box_office_revenue': 73340, 'runtime': 20450, 'release_date': 6902}}

- join the data

join inspection
joined ids: 42207
plot ids without metadata: 99
metadata ids without plot: 39534
first unmatched plot ids: ['10083650', '10153756', '10873999', '12651534', '13255982', '133671', '14481527', '14851642', '16758721', '16803295']

- cmu_data_processing
metadata records loaded: 81741
metadata path exits: True
plot path exits: True
limit: 500
output: data\processed\cmu_movies_sample.jsonl

- join cmu metadata with plots for processing
metadata records loaded: 81741
plot record loaded: 42306
joined records: 42207

- filter cmu movie for english sample

records built: 500
first title: The Hunger Games

## 30/5/26
- make sure that all ports and password are consistent
- created movie table
movies table ready
- loaded cmu sample data into database
movies loaded: 500
- added basic movie database search on sample
(.venv) D:\WhichMovieItIs> python.exe -c "from backend.app.services.search import search_movies; print([m['title'] for m in search_movies('Hunger Games', 3)])"
['The Hunger Games']
- added the search (/search) api endpoint

## 1/6/26
- make the frontend 
- connected the search api to the frontend
(![bacis frontend for the checking search api](image.png))

- loaded full 42k+ movies in database
records written: 42207
output: data\processed\cmu_movies_full.jsonl
metadata records loaded: 81741
metadata path exits: True
plot path exits: True
limit: 0
output: data\processed\cmu_movies_full.jsonl

metadata records loaded: 81741
plot record loaded: 42306
joined records: 42207

records built: 42207
first title: Taxi Blues

- verified the search still work
![verfied search still work](image-1.png)

## 2/6/26
- implemented the full-text search 
- added genrated search_vector column with weight title and plot summay
- gin index for faster text search
- output:

love => [('Bodyguard', 14.400001), ('God of Love', 12.2), ('Orange', 6.8), ('Pyaar Ishq Aur Mohabbat', 6.8), ('Kadhir', 6.4), ('Mohabbatein', 6.0), ('Moulin Rouge!', 6.0), ('Saawariya', 6.0), ('Save The Last Dance for Me', 6.0), ('Summer Wars', 6.0), ('When in Rome', 6.0), ('All About Love', 5.8), ('Love Actually', 5.8), ('Cyrano de Bergerac', 5.6), ('Down with Love', 5.4), ('Albela', 5.2), ('Dil To Pagal Hai', 5.2), ('Kurt & Courtney', 5.2), ('Pasión de gavilanes', 5.2), ('Super Star', 5.2)]
war => [('Oh! What a Lovely War', 5.0), ('Breaker Morant', 4.8), ("The War You Don't See", 4.6), ('Born on the Fourth of July', 4.4), ('North and South', 4.4), ('The Life and Death of Colonel Blimp', 4.4), ('Hiroshima', 4.0), ('InuYasha the Movie: Fire on the Mystic Island', 4.0), ('The Weight of Chains', 4.0), ('Prelude to War', 3.8), ('Robot Chicken: Star Wars Episode II', 3.8), ('War Horse', 3.8), ('Birthday Boy', 3.6), ('Einstein and Eddington', 3.6), ('Iluminados Por El Fuego', 3.6), ('Mother Night', 3.6), ('The Young Lions', 3.6), ('Week-End at the Waldorf', 3.6), ('American Drug War: The Last White Hope', 3.4), ('Babylon 5: In the Beginning', 3.2)]
lightsaber => [('The Formula', 3.2), ('LEGO Star Wars: Revenge of the Brick', 1.6), ('Star Wars Episode III: Revenge of the Sith', 1.2), ('Duality', 0.8), ('Starcrash', 0.8), ('Star Wars Episode IV: A New Hope', 0.8), ('Star Wars Episode V: The Empire Strikes Back', 0.8), ('Star Wars: The Clone Wars', 0.8), ('Hardware Wars', 0.4), ('Keroro Gunso the Super Movie 3: Keroro vs. Keroro Great Sky Duel', 0.4), ('Lego Star Wars: The Quest for R2-D2', 0.4), ('Leprechaun 4: In Space', 0.4), ('Robot Chicken: Star Wars Episode II', 0.4), ('Something, Something, Something Dark Side', 0.4), ('Star Wars Episode II: Attack of the Clones', 0.4), ('Star Wars Episode I: The Phantom Menace', 0.4), ('Star Wars Episode VI: Return of the Jedi', 0.4)]
hunger games => [('The Hunger Games: Catching Fire', 2.375), ('The Hunger Games', 1.815271), ('Iluminados Por El Fuego', 0.008696), ('The Aqua Teen Hunger Force Movie Film for Theatres', 0.004938), ('Resurrection of the Little Match Girl', 0.004444), ('Darling', 0.00396), ('Winnie the Pooh and a Day for Eeyore', 0.003618), ('Kaal', 0.002128), ('Crusade in Jeans', 0.00113), ('Shorts', 0.000881)]
zzzxxy => []

- added search evaluation scripts


## 3/6/26
- installed sentence-transformer embedding dependency
- apended embedding movie column using pgvector
- added embedding servise for movie and query text
- write the script to genrate embeddings for full cmu movie data
- added vector search service and `/search/vector` endpoint
- also write the script for the comparing the both search

-final output, vector search working:
query: hunger games
full-text: The Hunger Games: Catching Fire | The Hunger Games | Iluminados Por El Fuego | The Aqua Teen Hunger Force Movie Film for Theatres | Resurrection of the Little Match Girl
vector: The Hunger | The Hunger Games: Catching Fire | The Hunger Games | Games Men Play | Hunger

query: lightsaber
full-text: The Formula | LEGO Star Wars: Revenge of the Brick | Star Wars Episode III: Revenge of the Sith | Duality | Starcrash
vector: The Lightning Warrior | Bushido Blade | Masters of Menace | 3 Ninjas | Duel to the Death

query: god of love
full-text: Late One Night | The Love God? | Winter Light | God of Love | The Color of Paradise
vector: Man of God | Oh, God! Book II | Saving God | Salvation! | And Thou Shalt Love

query: oh what a lovely war
full-text: Oh! What a Lovely War | Khan Kluay 2 | Oh Shucks! Here Comes UNTAG | Merlin | The Hand of Fear
vector: Oh! What a Lovely War | In Love and War | Le Jeu | The Invaders | Gordon's War

query: zzzxxy
full-text: <no result>
vector: Zyzzyx Road | Macross Dynamite 7 | Decalogue VIII | Zzyzx | Zona Zamfirova

## 4-5/6/26
- added hybrid search, by using the rrf hybrid ranking
- by combining full-text search and vector search
- added `/search/hybrid` endpoint in Fastapi
- updated `scripts/compare_search_modes.pu` to compare:
    - full-text search
    - vector search 
    - hybrid search
- updated `scripts/evaluate_search.py` to support search modes:
    - full text
    - vector
    - hybrid
- fixed respone key "results" to "results"
- fixed f-string quote bug in  `compare_search_modes.py`

## 7-9/6/26
- done the reranked work
- added the cross-encoder on hybrid search
- added `/search/reranked` backend endpoint
- added `reranked` mode in search evaluation
- added reranked output to compare script

## 15/6/26
- completed ranked search evaluation baseline
- updated `scripts/evaluate_search.py` from simple pass/fail output to ranked
retrieval metrics:
- `hit@5`
- `mrr@10`
- `recall@10`
- `ndcg@10`
- `no_result_correct`
- `avg_latency_ms`
- `p95_latency_ms`
- added support for running all search modes in one command:
- `full-text`
- `vector`
- `hybrid`
- `reranked`
- generated the result file:
- `evals/search-evaluation.json`

## 18-20/6/26
- make the hybrid as the default search
- added the cached hybrid parameter tuning
- changed backend `/search` to hybrid retrieval
- expanded the evaluation quires from 13 to 50
- added dialogue-memory and character-memory intents
- verified all 75 referenced movie IDs and titles against PostgreSQL
- generated the expanded search evaluation baseline

## 21/6/25
- improved the no-result precision without reducing ranked retrieval quality.
- analyzed raw full-text and vector evidence for all 50 qrels
- identified no-result false positives as weak vector-only matches
- tested vector-only confidence thresholds
- selected threshold `0.50`
- added a query-level no-result guard to hybrid search
- updated the hybrid tuning script to model the production guard
- verified all five no-result qrels return no results
- verified ranked metrics remain unchanged
- improved hybrid no-result accuracy from `0.40` to `1.00`
- improved reranked no-result accuracy from `0.40` to `1.00`

## 21/6/26

- created a reusable candidate recall analysis script
- analyzed all 50 search qrels at candidate depth 50
- separated failures into:
  - ranking failures
  - candidate recall failures
  - vector-threshold filtered failures
  - no-result cases
- measured accepted candidate recall@50 at 0.7111
- measured raw candidate recall@50 at 0.7333
- identified 12 failures where the relevant movie never entered either
  candidate source
- identified one relevant movie filtered by the vector score threshold
- added targeted case inspection to the comparison script
- documented which failures are retrieval problems and which require
  additional dialogue data
- kept production hybrid behavior unchanged

## 21-22/6/26

- implemented strict minimum-match lexical retrieval
- used PostgreSQL term normalization and stemming
- cached full-text, vector, and broad candidates for evaluation
- tested broad RRF weights from 0.5 to 4.0
- selected experimental broad weight 3.0
- improved candidate recall@50 from 0.7111 to 0.8000
- improved hybrid Hit@5 from 0.6000 to 0.6667
- improved MRR@10 from 0.4926 to 0.5557
- preserved no-result accuracy at 1.0000
- improved three previously failed queries
- recorded zero Hit@5 regressions
- kept production hybrid behavior unchanged

## 21-23/6/26

- promoted minimum-match broad lexical retrieval into production hybrid search
- added broad retrieval weight `3.0`
- extended reciprocal-rank fusion from two sources to three sources
- updated the no-result guard to recognize broad lexical evidence
- added unit tests for fusion, deduplication, and no-result behavior
- added FastAPI blank-query regression coverage
- added PostgreSQL integration tests for broad retrieval
- updated candidate-recall analysis for all production sources
- reproduced candidate recall@50 of `0.8000`
- reproduced hybrid Hit@5 of `0.6667`
- preserved no-result accuracy at `1.0000`
- documented the production retrieval architecture
- kept reranking experimental

## 22-23/6/26

- added TMDB metadata columns to the movie catalog
- added safe title and release-year TMDB matching
- added cached poster enrichment for the existing 42,207 movies
- returned TMDB poster metadata through every retrieval source
- added poster URL construction without storing duplicated URLs
- added poster, genre, release year, and plot result cards
- added missing-poster fallback behavior
- verified metadata integration did not change retrieval metrics

## 26/6/26

- added document-level search tables for production retrieval experiments
- indexed CMU plot summaries as first-class search documents
- parsed CMU CoreNLP files into entity, action, keyword, and coreference search signals
- indexed CMU character metadata as cast and character search documents
- added document embedding backfill for the new search document index
- added `/search/documents` as an experimental v2 retrieval endpoint
- kept `/search` stable on the existing production hybrid pipeline
- added evaluation support for `document-hybrid`

## 28/6/26
- optimized document retrieval to retrieve top matching documents before grouping to movies
- added experimental `hybrid-v2` search using movie-level and document-level candidates
- added `/search/hybrid-v2` without changing the stable `/search` endpoint
- added `hybrid-v2` to search evaluation and comparison tooling
- added regression analysis for `hybrid` vs `hybrid-v2`
- tested hybrid-v2 fusion, no-result guard behavior, and API response behavior
- documented the production, document, and hybrid-v2 search paths

## 28/6/26 
- decided not to promote `hybrid-v2` because it had no improvements, one regression, and higher latency
- added `movie_memory_clues` as a production hybrid candidate source
- seeded memory clues for iconic quotes, objects, scenes, franchise aliases, and character memories
- fused memory clue results into the existing `/search` hybrid ranking
- updated candidate recall analysis to include memory clue evidence
- evaluated current `hybrid` again after memory clue fusion
- kept `/search/documents` and `/search/hybrid-v2` experimental

## 30-2/7/26
- added final TMDB movie ingestion for new TMDB-only movies
- added stable movie identity using `movie_key` and external TMDB IDs
- imported TMDB overview, tagline, keywords, credits, posters, and metadata into local search tables
- fixed TMDB importer update-path bug and insert/update control flow
- fixed search result row shape across vector, broad, and document search after adding `movie_key`
- added runtime TMDB exact-title fallback for missing movies
- verified runtime fallback with missing TMDB titles and confirmed next searches use the local database
- measured optimized runtime import latency at about `1.6s` for first missing-title import and about `160ms` after import