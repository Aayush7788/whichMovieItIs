import "./App.css"

function App(){
  return(
    <main className="app-shell">
      <section>
        <p className="eyebrow">WhichMovieItIs</p>
        <h1>Find the movie from a scene you remember</h1>
        <p className="subtitle">
          Search by rough plot, memory, or partial movie description.
        </p>

        <form className="search-form">
          <input type="text" placeholder="Example: Spaceship enter in wormhole." />
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