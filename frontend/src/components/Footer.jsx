export function Footer({ onFilmsClick }) {
  return (
    <footer className="site-footer">
      <div>
        <strong>WhichMovieItIs</strong>
        <p>Find movies from the scene you remember.</p>
      </div>

      <div>
        <span>Product</span>
        <button type="button" onClick={onFilmsClick}>Films</button>
        <a href="#home">Search</a>
      </div>

      <div>
        <span>Data</span>
        <p>CMU Movie Summary Corpus with TMDB posters and metadata when available.</p>
      </div>
    </footer>
  );
}
