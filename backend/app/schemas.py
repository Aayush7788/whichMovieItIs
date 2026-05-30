from pydantic import BaseModel

class MovieSearchResult(BaseModel):
    wikipedia_movie_id: str
    title: str
    release_date = str | None
    genres: list[str]
    plot_summary: str
    score: float | None

class MovieSearchResponse(BaseModel):
    query: str
    results: list[MovieSearchResult]