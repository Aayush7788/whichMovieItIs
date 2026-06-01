import { useState } from "react";
import "./App.css"

function App(){

  const [query, setQuery] = useState("");

  function handleSearch(event) {
    event.preventDefault();
    console.log(query);
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
          <button type="submit">Search</button>
        </form>
      </section>

      <section className="results-section">
        <p className="mutted">Foundings!</p>
      </section>
    </main>
  );
}

export default App;