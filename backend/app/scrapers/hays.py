from .base import JobResult, ScrapeResult

DISPLAY_NAME = "Hays NZ"
SOURCE = "hays"


async def scrape(keywords: str) -> ScrapeResult:
    # Hays NZ is a JavaScript SPA (Angular app) — listings are not in the initial HTML.
    encoded = keywords.replace(" ", "%20")
    search_url = f"https://www.hays.net.nz/job-search#fe_all_keyword={encoded}&fe_8_keyword={encoded}"
    return ScrapeResult(
        source=SOURCE,
        display_name=DISPLAY_NAME,
        jobs=[],
        error="Hays requires a browser to load listings",
        search_url=search_url,
    )
