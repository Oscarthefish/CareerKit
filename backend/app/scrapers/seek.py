from .base import JobResult, ScrapeResult

DISPLAY_NAME = "Seek NZ"
SOURCE = "seek"


async def scrape(keywords: str) -> ScrapeResult:
    # Seek NZ uses client-side JavaScript rendering — their job listings are not
    # accessible via plain HTTP requests. Open the search URL directly in your browser.
    encoded = keywords.replace(" ", "+")
    search_url = f"https://www.seek.co.nz/jobs?keywords={encoded}&location=All+New+Zealand"
    return ScrapeResult(
        source=SOURCE,
        display_name=DISPLAY_NAME,
        jobs=[],
        error="Seek requires a browser to load listings",
        search_url=search_url,
    )
