from pydantic import BaseModel

class MovieSearchResult(BaseModel):
    movie_key: str
    wikipedia_movie_id: str | None = None
    title: str
    release_date: str | None = None
    genres: list[str]
    plot_summary: str
    tmdb_id: int | None = None
    poster_path: str | None = None
    poster_url: str | None = None
    metadata_source: str | None = None
    score: float | None = None

class MovieSearchResponse(BaseModel):
    query: str
    results: list[MovieSearchResult]