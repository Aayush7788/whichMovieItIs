import { useState } from "react";
import "./App.css"

function App(){

  const [query, setQuery] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState([]);
  const [status, setStatus] = useState("idle");

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

      const response = await fetch(`/api/search/hybrid?${params.toString()}`);
      if(!response.ok){
        throw new Error(`Search failed with status ${response.status}`)
      }

      const data = await response.json();
      setResult(data.results);
      setStatus("success");
    } catch (error) {
      setResult([]);
      setStatus("error");
      setErrorMessage(error.message);
    }
    console.log(cleanedQuery);
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
          <p className="muted">No matches found in the current sample data</p>
        )}
        {status === "success" && result.length > 0 && (
          <div className="result-list">
            {result.map((movie)=>(
              <article className="movie-card" key={movie.wikipedia_movie_id}>
                <h2>{movie.title}</h2>
                {movie.release_date && <p>{movie.release_date}</p>}
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

export default App;