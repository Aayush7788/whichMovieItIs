import { exampleQueries } from "../data/homeContent";

export function HeroSearch({
  query,
  status,
  onQueryChange,
  onSearch,
  onExampleClick,
}) {
  function handleSubmit(event) {
    event.preventDefault();
    onSearch(query);
  }

  return (
    <section className="hero-section" id="home">
      <div className="hero-copy">
        <p className="eyebrow">Movie search from memory</p>
        <h1>Find Any Movie By Description</h1>
        <p className="subtitle">
          Describe a scene, plot, character, object, or exact title.
          WhichMovieItIs searches your local movie database and returns
          ranked matches.
        </p>
      </div>

      <form className="search-panel" onSubmit={handleSubmit}>
        <div className="search-input-row">
          <label htmlFor="movie-search">A movie where</label>
          <textarea
            id="movie-search"
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                onSearch(query);
              }
            }}
            placeholder="a guy wakes up and does not remember anything..."
            maxLength={1000}
            rows={3}
          />
        </div>

        <div className="search-actions">
          <span>{query.length}/1000</span>
          <span>Press Enter to search</span>
          <button type="submit" disabled={status === "loading"}>
            {status === "loading" ? "Searching" : "Find Movies"}
          </button>
        </div>
      </form>

      <div className="example-block">
        <span>Example descriptions</span>
        <div className="example-list">
          {exampleQueries.map((exampleQuery) => (
            <button
              type="button"
              key={exampleQuery}
              onClick={() => onExampleClick(exampleQuery)}
            >
              "{exampleQuery}"
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
