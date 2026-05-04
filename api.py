"""
start.gg API client.

Pure functions — no UI, no file I/O for credentials.
Credentials are passed in from the caller (the PyWebView bridge).
"""

import csv
import time
from pathlib import Path

import requests

API_URL = "https://api.start.gg/gql/alpha"

USER_ID_QUERY = """
query GetUserId($slug: String!) {
  user(slug: $slug) {
    id
    name
  }
}
"""

OWNED_TOURNAMENTS_QUERY = """
query TournamentsByOwner($ownerId: ID!, $page: Int!) {
  tournaments(query: {
    perPage: 50,
    page: $page,
    filter: { ownerId: $ownerId }
  }) {
    pageInfo { totalPages }
    nodes {
      id
      name
      numAttendees
      startAt
    }
  }
}
"""


class StartGGError(Exception):
    """Raised when the start.gg API returns an error or unexpected response."""


def _post(token: str, query: str, variables: dict) -> dict:
    """Send a GraphQL request and return the parsed JSON, raising on errors."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            API_URL,
            json={"query": query, "variables": variables},
            headers=headers,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise StartGGError(f"Network error: {exc}") from exc

    if response.status_code == 401:
        raise StartGGError("Invalid API token (401 Unauthorized).")
    if response.status_code == 429:
        raise StartGGError("Rate limited by start.gg. Try again in a minute.")
    if not response.ok:
        raise StartGGError(f"HTTP {response.status_code} from start.gg.")

    data = response.json()
    if "errors" in data:
        raise StartGGError(data["errors"][0].get("message", "Unknown API error"))
    return data


def lookup_user(token: str, slug: str) -> dict:
    """Return {'id': ..., 'name': ...} for the given user slug."""
    formatted = slug if slug.startswith("user/") else f"user/{slug}"
    data = _post(token, USER_ID_QUERY, {"slug": formatted})
    user = data.get("data", {}).get("user")
    if not user:
        raise StartGGError(f"No user found for slug '{slug}'.")
    return user


def fetch_owned_tournaments(token: str, slug: str, progress_cb=None) -> list[dict]:
    """
    Fetch every tournament owned/created by the user with the given slug.

    `progress_cb`, if provided, is called as progress_cb(current_page, total_pages)
    after each page so the UI can update a progress bar.
    """
    user = lookup_user(token, slug)
    owner_id = user["id"]

    tournaments = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        data = _post(
            token,
            OWNED_TOURNAMENTS_QUERY,
            {"ownerId": owner_id, "page": page},
        )
        block = data.get("data", {}).get("tournaments")
        if not block:
            break

        total_pages = block["pageInfo"]["totalPages"]

        for t in block["nodes"]:
            if not t:
                continue
            tournaments.append({
                "id": t["id"],
                "name": t["name"],
                "attendees": t["numAttendees"] or 0,
                "start_at": t["startAt"],
            })

        if progress_cb:
            progress_cb(page, total_pages)

        page += 1
        time.sleep(0.5)  # be polite to the API

    return tournaments


def export_to_csv(tournaments: list[dict], path: str) -> str:
    """Write tournaments to a CSV file. Returns the resolved absolute path."""
    out_path = Path(path).expanduser().resolve()
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["Tournament Name", "Attendees", "Start Date"]
        )
        writer.writeheader()
        for t in tournaments:
            start = ""
            if t.get("start_at"):
                start = time.strftime("%Y-%m-%d", time.gmtime(t["start_at"]))
            writer.writerow({
                "Tournament Name": t["name"],
                "Attendees": t["attendees"],
                "Start Date": start,
            })
    return str(out_path)
