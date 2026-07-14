import { MovieGrid } from "./MovieGrid";
import { PanelState } from "./PanelState";
import { SectionHeader } from "./SectionHeader";

export function MovieShelf({
  eyebrow,
  title,
  description,
  movies,
  status,
  error,
  actionLabel,
  onActionClick,
  onMovieClick,
  children,
}) {
  return (
    <section className="content-section">
      <SectionHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actionLabel={actionLabel}
        onActionClick={onActionClick}
      />

      {movies.length > 0 ? (
        <>
          <MovieGrid movies={movies} onMovieClick={onMovieClick} />
          {children}
        </>
      ) : (
        <CatalogState status={status} error={error} />
      )}
    </section>
  );
}

function CatalogState({ status, error }) {
  if (status === "loading") {
    return <PanelState>Loading films...</PanelState>;
  }

  if (status === "error") {
    return <PanelState tone="error">{error}</PanelState>;
  }

  return <PanelState>No films loaded yet.</PanelState>;
}
