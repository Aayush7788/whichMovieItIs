import { useState } from "react";

function getPosterInitial(title) {
  return title?.trim().slice(0, 1).toUpperCase() || "?";
}

export function MoviePoster({ src, title, size = "card" }) {
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  const showImage = Boolean(src) && !failed;
  const showFallback = !showImage || !loaded;
  const fallbackClassName = [
    "poster-fallback",
    size === "large" ? "large" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <>
      {showImage && (
        <img
          className={loaded ? "poster-image loaded" : "poster-image"}
          src={src}
          alt={`${title} poster`}
          loading={size === "large" ? "eager" : "lazy"}
          onLoad={() => setLoaded(true)}
          onError={() => setFailed(true)}
        />
      )}

      {showFallback && (
        <div className={fallbackClassName}>
          <strong>{getPosterInitial(title)}</strong>
          <span>
            {showImage ? "Loading poster" : "Poster unavailable"}
          </span>
        </div>
      )}
    </>
  );
}
