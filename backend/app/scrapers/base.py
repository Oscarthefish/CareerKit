from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class JobResult:
    title: str
    url: str
    source: str
    job_key: str          # unique dedup key: "source:id"
    company: Optional[str] = None
    location: Optional[str] = None
    description_snippet: Optional[str] = None
    date_posted: Optional[str] = None


@dataclass
class ScrapeResult:
    source: str
    display_name: str
    jobs: List[JobResult] = field(default_factory=list)
    error: Optional[str] = None
    search_url: Optional[str] = None   # fallback browse link when scraping is unavailable


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-NZ,en;q=0.9",
}

JSON_HEADERS = {
    **HEADERS,
    "Accept": "application/json, text/plain, */*",
}
