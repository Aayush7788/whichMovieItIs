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
      setResults([]);
      return;
    }
    setStatus("loading");
    setErrorMessage("");

    try{
      const params = new URLSearchParams({
        q: cleanedQuery,
        limit: "5",
      });

      const response = await fetch(`\api\search?${params.toString()}`);
      if(!response.ok){
        throw new Error(`Search failed with status ${response.status}`)
      }

      const data = await response.json();
      setResult(data.result);
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
        {errorMessage ? 
        (<p className="error-message">{errorMessage}</p>) :
        (<p className="mutted">Foundings!</p>)
        }
      </section>
    </main>
  );
}

export default App;