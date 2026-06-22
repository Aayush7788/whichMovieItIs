import { useState } from "react";
import "./App.css"

function App(){

  const [query, setQuery] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState([]);
  const [status, setStatus] = useState("idle");
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || "/api";

  async function handleSearch(event) {
    event.preventDefault();

    const cleanedQuery = query.trim();
    if(!cleanedQuery){
      setStatus("error");
      setErrorMessage("Search for a movie or scene first");
      setResult([]);
      return;
    }
    setStatus("loading");
    setErrorMessage("");

    try{
      const params = new URLSearchParams({
        q: cleanedQuery,
        limit: "5",
      });

      const response = await fetch(`${apiBaseUrl}/search?${params.toString()}`);
      if (!response.ok) {
        const errorData = await response
        .json()
        .catch(() => null);

      throw new Error(
        errorData?.detail ||
        `Search failed with status ${response.status}`
      );
      }

      const data = await response.json();
      setResult(data.results);
      setStatus("success");
    } catch (error) {
      setResult([]);
      setStatus("error");
      setErrorMessage(error.message);
    }
    
  }

  return(
    <main className="app-shell">
      <section>
        <p className="eyebrow">WhichMovieItIs</p>
        <h1>Find the movie from a scene you remember</h1>
        <p className="subtitle">
          Search by rough plot, memory, or partial movie description.
        </p>

        <form className="search-form" onSubmit={handleSearch}>
          <input type="text" 
            value={query} 
            onChange={(event) => setQuery(event.target.value)} 
            placeholder="Example: Spaceship enter in wormhole." 
          />
          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "searching...": "search"}  
          </button>
        </form>
      </section>

      <section className="results-section">
        { status === "idle" && (
          <p className="muted"> Search results </p>
        )}
        {status === "loading" && (
          <p className="muted">Searching movies...</p>
        )}
        {status === "error" && (
          <p className="error-message">{errorMessage}</p>
        )}
        {status === "success" && result.length === 0 && (
          <p className="muted">No confident match found in the current movie database.</p>
        )}
        {status === "success" && result.length > 0 && (
          <div className="result-list">
            {result.map((movie, index) => (
            <article
            className="movie-card"
            key={movie.wikipedia_movie_id}
            >
                <div className="poster-frame">
                  {movie.poster_url ? (
                    <img
                      className="movie-poster"
                      src={movie.poster_url}
                      alt={`${movie.title} poster`}
                      loading="lazy"
                    />
                  ) : (
                  <div className="poster-placeholder">
                    Poster unavailable
                  </div>
                )}
              </div>

              <div className="movie-content">
                <div className="movie-title-row">
                  <span className="result-rank">
                    {index + 1}
                  </span>

                  <div>
                    <h2>{movie.title}</h2>

                    {movie.release_date && (
                      <p className="release-year">
                        {movie.release_date.slice(0, 4)}
                      </p>
                    )}
                  </div>
                </div>

                {movie.genres?.length > 0 && (
                  <div className="genre-list">
                    {movie.genres.slice(0, 4).map((genre) => (
                      <span
                        className="genre-chip"
                        key={genre}
                      >
                        {genre}
                      </span>
                    ))}
                  </div>
                )}

                <p className="plot-summary">
                  {movie.plot_summary}
                </p>
              </div>
            </article>
          ))}
        </div>
      )}
      </section>
    </main>
  );
}

export default App;