import { formatSource, getReleaseYear } from "../lib/format";

export function MovieCard({ movie, rank, onClick }) {
  const releaseYear = getReleaseYear(movie.release_date);

  return (
    <button
      type="button"
      className="movie-card"
      onClick={onClick}
      aria-label={`Open details for ${movie.title}`}
    >
      <div className="poster-area">
        {rank && <span className="rank-badge">{rank}</span>}

        {movie.poster_url ? (
          <img
            src={movie.poster_url}
            alt={`${movie.title} poster`}
            loading="lazy"
          />
        ) : (
          <div className="poster-fallback">
            <strong>{movie.title.slice(0, 1)}</strong>
            <span>Poster unavailable</span>
          </div>
        )}
      </div>

      <div className="movie-card-body">
        <h3>{movie.title}</h3>
        <p className="movie-meta">
          {releaseYear && <span>{releaseYear}</span>}
          {movie.source && <span>{formatSource(movie.source)}</span>}
        </p>
        {movie.genres?.length > 0 && (
          <p className="movie-genres">
            {movie.genres.slice(0, 2).join(" / ")}
          </p>
        )}
      </div>
    </button>
  );
}
