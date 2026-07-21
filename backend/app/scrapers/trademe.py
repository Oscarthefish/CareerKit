from .base import JobResult, ScrapeResult

DISPLAY_NAME = "Trade Me Jobs"
SOURCE = "trademe"


async def scrape(keywords: str) -> ScrapeResult:
    # Trade Me Jobs is JavaScript-rendered — listings are not in the initial HTML.
    encoded = keywords.replace(" ", "+")
    search_url = f"https://www.trademe.co.nz/a/jobs/search?search_string={encoded}"
    return ScrapeResult(
        source=SOURCE,
        display_name=DISPLAY_NAME,
        jobs=[],
        error="Trade Me requires a browser to load listings",
        search_url=search_url,
    )
