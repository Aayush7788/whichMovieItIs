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

class MovieCatalogItem(BaseModel):
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
    source: str

class MovieCatalogResponse(BaseModel):
    results: list[MovieCatalogItem]
    total: int
    limit: int
    offset: int

class MovieDetail(MovieCatalogItem):
    freebase_movie_id: str | None = None
    box_office_revenue: float | None = None
    runtime: float | None = None
    languages: list[object]
    countries: list[object]
    search_boost_text: str | None = None
