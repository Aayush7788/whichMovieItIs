import { useEffect, useMemo, useState } from "react";

import { FaqSection } from "./components/FaqSection";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { HeroSearch } from "./components/HeroSearch";
import { HowItWorks } from "./components/HowItWorks";
import { MovieDetailModal } from "./components/MovieDetailModal";
import { MovieShelf } from "./components/MovieShelf";
import { SearchResultsSection } from "./components/SearchResultsSection";
import { getMovieDetail, getMovies, searchMovies } from "./lib/api";

const moviePageSize = 18;

function App() {
  const [query, setQuery] = useState("");
  const [searchStatus, setSearchStatus] = useState("idle");
  const [searchError, setSearchError] = useState("");
  const [searchResults, setSearchResults] = useState([]);

  const [movies, setMovies] = useState([]);
  const [movieTotal, setMovieTotal] = useState(0);
  const [moviesStatus, setMoviesStatus] = useState("idle");
  const [moviesError, setMoviesError] = useState("");

  const [activeSection, setActiveSection] = useState("home");
  const [selectedMovie, setSelectedMovie] = useState(null);
  const [detailStatus, setDetailStatus] = useState("idle");
  const [detailError, setDetailError] = useState("");

  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";
  const featuredMovies = useMemo(() => movies.slice(0, 6), [movies]);
  const hasMoreMovies = movies.length < movieTotal;

  useEffect(() => {
    let cancelled = false;

    async function loadInitialMovies() {
      setMoviesStatus("loading");
      setMoviesError("");

      try {
        const data = await getMovies(apiBaseUrl, {
          limit: moviePageSize,
          offset: 0,
        });

        if (cancelled) {
          return;
        }

        setMovies(data.results);
        setMovieTotal(data.total);
        setMoviesStatus("success");
      } catch (error) {
        if (cancelled) {
          return;
        }

        setMovies([]);
        setMoviesStatus("error");
        setMoviesError(error.message);
      }
    }

    loadInitialMovies();

    return () => {
      cancelled = true;
    };
  }, [apiBaseUrl]);

  useEffect(() => {
    function closeOnEscape(event) {
      if (event.key === "Escape") {
        setSelectedMovie(null);
        setDetailStatus("idle");
        setDetailError("");
      }
    }

    window.addEventListener("keydown", closeOnEscape);

    return () => window.removeEventListener("keydown", closeOnEscape);
  }, []);

  async function runSearch(rawQuery) {
    const cleanedQuery = rawQuery.trim();

    if (!cleanedQuery) {
      setSearchStatus("error");
      setSearchError("Describe a movie scene or title first.");
      setSearchResults([]);
      return;
    }

    setSearchStatus("loading");
    setSearchError("");
    setActiveSection("search");

    try {
      const data = await searchMovies(apiBaseUrl, cleanedQuery);

      setSearchResults(data.results);
      setSearchStatus("success");
    } catch (error) {
      setSearchResults([]);
      setSearchStatus("error");
      setSearchError(error.message);
    }
  }

  function runExampleSearch(exampleQuery) {
    setQuery(exampleQuery);
    runSearch(exampleQuery);
  }

  async function loadMoreMovies() {
    setMoviesStatus("loading");
    setMoviesError("");

    try {
      const data = await getMovies(apiBaseUrl, {
        limit: moviePageSize,
        offset: movies.length,
      });

      setMovies((currentMovies) => [
        ...currentMovies,
        ...data.results,
      ]);
      setMovieTotal(data.total);
      setMoviesStatus("success");
    } catch (error) {
      setMoviesStatus("error");
      setMoviesError(error.message);
    }
  }

  async function openMovieDetail(movieKey) {
    setSelectedMovie(null);
    setDetailError("");
    setDetailStatus("loading");

    try {
      const movie = await getMovieDetail(apiBaseUrl, movieKey);

      setSelectedMovie(movie);
      setDetailStatus("success");
    } catch (error) {
      setDetailError(error.message);
      setDetailStatus("error");
    }
  }

  function closeMovieDetail() {
    setSelectedMovie(null);
    setDetailStatus("idle");
    setDetailError("");
  }

  function showFilms() {
    setActiveSection("films");
    requestAnimationFrame(() => {
      document
        .getElementById("films")
        ?.scrollIntoView({ behavior: "smooth" });
    });
  }

  return (
    <main className="app-shell">
      <Header activeSection={activeSection} onFilmsClick={showFilms} />

      <HeroSearch
        query={query}
        status={searchStatus}
        onQueryChange={setQuery}
        onSearch={runSearch}
        onExampleClick={runExampleSearch}
      />

      <SearchResultsSection
        status={searchStatus}
        errorMessage={searchError}
        results={searchResults}
        onMovieClick={openMovieDetail}
      />

      <MovieShelf
        eyebrow="Featured from database"
        title="Poster-backed films"
        movies={featuredMovies}
        status={moviesStatus}
        error={moviesError}
        actionLabel="Open Films"
        onActionClick={showFilms}
        onMovieClick={openMovieDetail}
      />

      <div id="films">
        <MovieShelf
          eyebrow={`${movieTotal.toLocaleString()} movies indexed`}
          title="Films"
          description="Browse movies currently stored in your PostgreSQL database."
          movies={movies}
          status={moviesStatus}
          error={moviesError}
          onMovieClick={openMovieDetail}
        >
          {hasMoreMovies && (
            <div className="load-more-row">
              <button
                type="button"
                className="secondary-button"
                onClick={loadMoreMovies}
                disabled={moviesStatus === "loading"}
              >
                {moviesStatus === "loading"
                  ? "Loading more films"
                  : "Load more films"}
              </button>
            </div>
          )}
        </MovieShelf>
      </div>

      <HowItWorks />
      <FaqSection />
      <Footer onFilmsClick={showFilms} />

      <MovieDetailModal
        movie={selectedMovie}
        status={detailStatus}
        error={detailError}
        onClose={closeMovieDetail}
      />
    </main>
  );
}

export default App;
