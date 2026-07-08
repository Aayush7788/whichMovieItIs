import { MovieGrid } from "./MovieGrid";
import { PanelState } from "./PanelState";
import { SectionHeader } from "./SectionHeader";

export function SearchResultsSection({
  status,
  errorMessage,
  results,
  onMovieClick,
}) {
  if (status === "idle") {
    return null;
  }

  return (
    <section className="content-section search-results-section">
      <SectionHeader
        eyebrow="Hybrid search"
        title="Best matches"
        description="Ranked with full-text, vector, broad lexical, and memory clue signals."
      />

      {status === "loading" && (
        <PanelState>Searching movies...</PanelState>
      )}

      {status === "error" && (
        <PanelState tone="error">{errorMessage}</PanelState>
      )}

      {status === "success" && results.length === 0 && (
        <PanelState>
          No confident match found. Add a unique object, ending,
          character, year, or exact title.
        </PanelState>
      )}

      {status === "success" && results.length > 0 && (
        <MovieGrid
          movies={results}
          onMovieClick={onMovieClick}
          showRank
        />
      )}
    </section>
  );
}
