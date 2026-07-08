export function Header({ activeSection, onFilmsClick }) {
  return (
    <header className="site-header">
      <a className="brand" href="#home" aria-label="WhichMovieItIs home">
        <span className="brand-mark">W</span>
        <span>WhichMovieItIs</span>
      </a>

      <nav className="main-nav" aria-label="Primary navigation">
        <button
          type="button"
          className={activeSection === "films" ? "active" : ""}
          onClick={onFilmsClick}
        >
          Films
        </button>
      </nav>
    </header>
  );
}
