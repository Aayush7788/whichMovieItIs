import re
import time

import httpx

from backend.app.config import settings


retryable_status_codes = {
    429,
    500,
    502,
    503,
    504,
}

title_separator_pattern = re.compile(r"[^a-z0-9]+")
release_year_pattern = re.compile(r"\d{4}")


def normalize_title(title: str) -> str:
    normalized = title_separator_pattern.sub(
        " ",
        title.casefold(),
    )
    return " ".join(normalized.split())


def extract_release_year(
    release_date: str | None,
) -> str | None:
    if not release_date:
        return None

    match = release_year_pattern.search(release_date)

    if match is None:
        return None

    return match.group(0)


def build_poster_url(
    poster_path: str | None,
) -> str | None:
    if not poster_path:
        return None

    normalized_path = "/" + poster_path.lstrip("/")

    return (
        f"{settings.tmdb_image_base_url}/"
        f"{settings.tmdb_poster_size}"
        f"{normalized_path}"
    )


def create_tmdb_client() -> httpx.Client:
    if not settings.tmdb_read_access_token:
        raise RuntimeError(
            "TMDB_READ_ACCESS_TOKEN is not configured"
        )

    return httpx.Client(
        base_url=settings.tmdb_api_base_url,
        headers={
            "Authorization": (
                "Bearer "
                f"{settings.tmdb_read_access_token}"
            ),
            "accept": "application/json",
        },
        timeout=settings.tmdb_timeout_seconds,
    )


def retry_delay_seconds(
    response: httpx.Response,
    attempt: int,
) -> float:
    retry_after = response.headers.get("Retry-After")

    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass

    return min(2 ** (attempt - 1), 8)


def request_tmdb_json(
    client: httpx.Client,
    path: str,
    params: dict[str, object],
    maximum_attempts: int = 4,
) -> dict[str, object]:
    for attempt in range(1, maximum_attempts + 1):
        response = client.get(path, params=params)

        if response.status_code not in retryable_status_codes:
            response.raise_for_status()
            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError(
                    "TMDB response must be a JSON object"
                )

            return payload

        if attempt == maximum_attempts:
            response.raise_for_status()

        time.sleep(
            retry_delay_seconds(response, attempt)
        )

    raise RuntimeError("TMDB request failed")


def choose_tmdb_match(
    results: list[dict[str, object]],
    title: str,
    release_date: str | None,
) -> dict[str, object] | None:
    expected_title = normalize_title(title)
    expected_year = extract_release_year(release_date)

    exact_title_matches = []

    for result in results:
        candidate_titles = {
            normalize_title(
                str(result.get("title") or "")
            ),
            normalize_title(
                str(result.get("original_title") or "")
            ),
        }

        if expected_title in candidate_titles:
            exact_title_matches.append(result)

    if expected_year:
        year_matches = [
            result
            for result in exact_title_matches
            if extract_release_year(
                str(result.get("release_date") or "")
            ) == expected_year
        ]

        if year_matches:
            return max(
                year_matches,
                key=lambda result: float(
                    result.get("popularity") or 0.0
                ),
            )

        return None

    if len(exact_title_matches) == 1:
        return exact_title_matches[0]

    return None


def search_tmdb_movie(
    client: httpx.Client,
    title: str,
    release_date: str | None,
) -> dict[str, object] | None:
    payload = request_tmdb_json(
        client=client,
        path="/search/movie",
        params={
            "query": title,
            "include_adult": "false",
            "language": "en-US",
            "page": 1,
        },
    )

    raw_results = payload.get("results")

    if not isinstance(raw_results, list):
        return None

    results = [
        result
        for result in raw_results
        if isinstance(result, dict)
    ]

    return choose_tmdb_match(
        results=results,
        title=title,
        release_date=release_date,
    )