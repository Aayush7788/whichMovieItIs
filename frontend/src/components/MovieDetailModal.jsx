import {
  formatList,
  formatMoney,
  formatRuntime,
  formatSource,
  getReleaseYear,
} from "../lib/format";
import { MoviePoster } from "./MoviePoster";

export function MovieDetailModal({
  movie,
  status,
  error,
  onClose,
}) {
  if (status === "idle") {
    return null;
  }

  if (status === "loading" || status === "error") {
    return (
      <DetailFrame onClose={onClose} compact>
        {status === "loading" && (
          <div className="detail-state">Loading movie details...</div>
        )}
        {status === "error" && (
          <div className="detail-state error-state">
            <h2>Could not load movie details</h2>
            <p>{error}</p>
          </div>
        )}
      </DetailFrame>
    );
  }

  if (!movie) {
    return null;
  }

  const releaseYear = getReleaseYear(movie.release_date);
  const languageText = formatList(movie.languages);
  const countryText = formatList(movie.countries);
  const externalId = getExternalId(movie);

  return (
    <DetailFrame onClose={onClose}>
      <div className="detail-layout">
        <div className="detail-poster">
          <MoviePoster
            src={movie.poster_url}
            title={movie.title}
            size="large"
          />
        </div>

        <div className="detail-content">
          <p className="detail-kicker">Movie details</p>
          <h2>{movie.title}</h2>

          <div className="detail-meta-row">
            {releaseYear && <span>{releaseYear}</span>}
            {movie.runtime > 0 && (
              <span>{formatRuntime(movie.runtime)}</span>
            )}
            {movie.source && <span>{formatSource(movie.source)}</span>}
            <span>{externalId}</span>
          </div>

          {movie.genres?.length > 0 && (
            <div className="genre-row">
              {movie.genres.slice(0, 6).map((genre) => (
                <span key={genre}>{genre}</span>
              ))}
            </div>
          )}

          <section className="detail-overview">
            <h3>Overview</h3>
            <p>{movie.plot_summary}</p>
          </section>

          <div className="detail-stat-grid">
            <DetailStat
              label="Release date"
              value={movie.release_date || "Unknown"}
            />
            <DetailStat
              label="Runtime"
              value={
                movie.runtime > 0
                  ? formatRuntime(movie.runtime)
                  : "Unknown"
              }
            />
            <DetailStat
              label="Box office"
              value={
                movie.box_office_revenue > 0
                  ? formatMoney(movie.box_office_revenue)
                  : "Unknown"
              }
            />
            <DetailStat
              label="Metadata"
              value={movie.metadata_source || movie.source}
            />
          </div>

          {(languageText || countryText) && (
            <div className="detail-extra">
              {languageText && (
                <p><strong>Languages:</strong> {languageText}</p>
              )}
              {countryText && (
                <p><strong>Countries:</strong> {countryText}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </DetailFrame>
  );
}

function DetailFrame({ children, onClose, compact = false }) {
  return (
    <div className="detail-backdrop" role="dialog" aria-modal="true">
      <article className={`detail-modal ${compact ? "compact" : ""}`}>
        <button
          type="button"
          className="detail-close"
          onClick={onClose}
          aria-label="Close movie details"
        >
          x
        </button>
        {children}
      </article>
    </div>
  );
}

function DetailStat({ label, value }) {
  return (
    <div className="detail-stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function getExternalId(movie) {
  if (movie.tmdb_id) {
    return `TMDB ${movie.tmdb_id}`;
  }

  if (movie.wikipedia_movie_id) {
    return `CMU ${movie.wikipedia_movie_id}`;
  }

  return movie.movie_key;
}
