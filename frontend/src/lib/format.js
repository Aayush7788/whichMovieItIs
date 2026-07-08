export function getReleaseYear(releaseDate) {
  if (!releaseDate) {
    return null;
  }

  return String(releaseDate).slice(0, 4);
}

export function formatSource(source) {
  return String(source || "")
    .replace("cmu_movie_summary_corpus", "CMU")
    .replace("tmdb", "TMDB")
    .replaceAll("_", " ");
}

export function formatRuntime(runtime) {
  return `${Math.round(Number(runtime))} min`;
}

export function formatMoney(value) {
  const numberValue = Number(value);

  if (numberValue >= 1_000_000_000) {
    return `$${(numberValue / 1_000_000_000).toFixed(1)}B`;
  }

  if (numberValue >= 1_000_000) {
    return `$${(numberValue / 1_000_000).toFixed(1)}M`;
  }

  return `$${numberValue.toLocaleString()}`;
}

export function formatList(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "";
  }

  return items
    .map((item) => {
      if (typeof item === "string") {
        return item.replace(" Language", "");
      }

      if (item && typeof item === "object") {
        return (
          item.english_name ||
          item.name ||
          item.iso_3166_1 ||
          item.iso_639_1
        );
      }

      return "";
    })
    .filter(Boolean)
    .slice(0, 6)
    .join(", ");
}
