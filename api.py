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
    player {
      gamerTag
    }
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
      slug
      numAttendees
      startAt
      isOnline
      city
      addrState
      countryCode
      venueName
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
    """Return {'id': ..., 'name': ..., 'gamer_tag': ...} for the given user slug."""
    formatted = slug if slug.startswith("user/") else f"user/{slug}"
    data = _post(token, USER_ID_QUERY, {"slug": formatted})
    user = data.get("data", {}).get("user")
    if not user:
        raise StartGGError(f"No user found for slug '{slug}'.")
    player = user.get("player") or {}
    user["gamer_tag"] = player.get("gamerTag") or user.get("name") or slug
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
                "slug": t.get("slug"),
                "attendees": t["numAttendees"] or 0,
                "start_at": t["startAt"],
                "is_online": bool(t.get("isOnline")),
                "city": t.get("city"),
                "state": t.get("addrState"),
                "country": t.get("countryCode"),
                "venue": t.get("venueName"),
            })

        if progress_cb:
            progress_cb(page, total_pages)

        page += 1
        time.sleep(0.5)  # be polite to the API

    return tournaments


def compute_stats(tournaments: list[dict]) -> dict:
    """
    Derive 'wrapped'-style stats from the raw tournament list.

    Returns a dict shaped for direct JSON consumption by the UI.
    """
    if not tournaments:
        return {
            "count": 0,
            "total_attendees": 0,
            "average_attendees": 0,
            "biggest": None,
            "first_event": None,
            "latest_event": None,
            "online_count": 0,
            "offline_count": 0,
            "unique_cities": 0,
            "unique_venues": 0,
            "by_year": [],
            "timeline": [],
        }

    total_attendees = sum(t["attendees"] for t in tournaments)
    count = len(tournaments)

    # Biggest single tournament
    biggest = max(tournaments, key=lambda t: t["attendees"])

    # Date range — only consider tournaments with a real startAt
    dated = [t for t in tournaments if t.get("start_at")]
    first_event = min(dated, key=lambda t: t["start_at"]) if dated else None
    latest_event = max(dated, key=lambda t: t["start_at"]) if dated else None

    # Online vs offline
    online_count = sum(1 for t in tournaments if t["is_online"])
    offline_count = count - online_count

    # Unique cities/venues (offline only — online tournaments don't have a real city)
    cities = {
        f"{t['city']}, {t['state'] or t['country'] or ''}".strip(", ")
        for t in tournaments
        if not t["is_online"] and t.get("city")
    }
    venues = {t["venue"] for t in tournaments if not t["is_online"] and t.get("venue")}

    # Tournaments per year (sorted asc)
    year_counts: dict[int, dict] = {}
    for t in dated:
        year = time.gmtime(t["start_at"]).tm_year
        bucket = year_counts.setdefault(year, {"year": year, "count": 0, "attendees": 0})
        bucket["count"] += 1
        bucket["attendees"] += t["attendees"]
    by_year = sorted(year_counts.values(), key=lambda x: x["year"])

    # Timeline: every dated tournament as a point, oldest first
    timeline = sorted(
        [
            {"date": t["start_at"], "name": t["name"], "attendees": t["attendees"]}
            for t in dated
        ],
        key=lambda x: x["date"],
    )

    def _summarize(t: dict | None) -> dict | None:
        if not t:
            return None
        return {
            "name": t["name"],
            "attendees": t["attendees"],
            "date": t.get("start_at"),
            "slug": t.get("slug"),
        }

    return {
        "count": count,
        "total_attendees": total_attendees,
        "average_attendees": round(total_attendees / count, 1),
        "biggest": _summarize(biggest),
        "first_event": _summarize(first_event),
        "latest_event": _summarize(latest_event),
        "online_count": online_count,
        "offline_count": offline_count,
        "unique_cities": len(cities),
        "unique_venues": len(venues),
        "by_year": by_year,
        "timeline": timeline,
    }


def export_to_csv(tournaments: list[dict], path: str) -> str:
    """Write tournaments to a CSV file. Returns the resolved absolute path."""
    out_path = Path(path).expanduser().resolve()
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "Tournament Name", "Attendees", "Start Date",
                "Online", "City", "State", "Country", "Venue",
            ],
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
                "Online": "Yes" if t.get("is_online") else "No",
                "City": t.get("city") or "",
                "State": t.get("state") or "",
                "Country": t.get("country") or "",
                "Venue": t.get("venue") or "",
            })
    return str(out_path)
