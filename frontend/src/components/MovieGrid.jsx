import { MovieCard } from "./MovieCard";

export function MovieGrid({ movies, onMovieClick, showRank = false }) {
  return (
    <div className="movie-grid">
      {movies.map((movie, index) => (
        <MovieCard
          key={movie.movie_key}
          movie={movie}
          rank={showRank ? index + 1 : null}
          onClick={() => onMovieClick(movie.movie_key)}
        />
      ))}
    </div>
  );
}
