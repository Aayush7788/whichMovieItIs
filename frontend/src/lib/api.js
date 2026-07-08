const retryableStatuses = new Set([408, 425, 429, 500, 502, 503, 504]);
const retryDelayMs = 500;
const maxAttempts = 5;

function wait(milliseconds) {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, milliseconds);
  });
}

function shouldRetry(error, attempt) {
  if (attempt >= maxAttempts) {
    return false;
  }

  return error.retryable === true || error instanceof TypeError;
}

async function responseError(response) {
  const errorData = await response
    .json()
    .catch(() => null);
  const error = new Error(
    errorData?.detail ||
    `Request failed with status ${response.status}`,
  );

  error.status = response.status;
  error.retryable = retryableStatuses.has(response.status);

  return error;
}

async function fetchJson(url) {
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(url);

      if (!response.ok) {
        throw await responseError(response);
      }

      return response.json();
    } catch (error) {
      lastError = error;

      if (!shouldRetry(error, attempt)) {
        throw error;
      }

      await wait(retryDelayMs * attempt);
    }
  }

  throw lastError;
}

export function searchMovies(apiBaseUrl, query, limit = 8) {
  const params = new URLSearchParams({
    q: query,
    limit: String(limit),
  });

  return fetchJson(`${apiBaseUrl}/search?${params.toString()}`);
}

export function getMovies(apiBaseUrl, { limit, offset }) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  return fetchJson(`${apiBaseUrl}/movies?${params.toString()}`);
}

export function getMovieDetail(apiBaseUrl, movieKey) {
  return fetchJson(
    `${apiBaseUrl}/movies/${encodeURIComponent(movieKey)}`,
  );
}
