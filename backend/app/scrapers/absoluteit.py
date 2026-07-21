import hashlib
import httpx
from bs4 import BeautifulSoup
from .base import JobResult, ScrapeResult, HEADERS

DISPLAY_NAME = "Absolute IT"
SOURCE = "absoluteit"
BASE_URL = "https://www.absoluteit.co.nz"


async def scrape(keywords: str) -> ScrapeResult:
    # AbsoluteIT doesn't have reliable keyword search — fetch all jobs and filter
    url = f"{BASE_URL}/jobs/"
    kw_lower = {k.lower() for k in keywords.split()}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers=HEADERS)
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")
        jobs = []

        for card in soup.select(".card-job"):
            # Title
            title_el = card.select_one(".card-job__title, h3, h2")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Individual job link — the "Read more" link goes to /it-job/slug/
            job_link = card.select_one("a[href*='/it-job/']")
            if not job_link:
                continue
            href = job_link.get("href", "")
            full_url = href if href.startswith("http") else f"{BASE_URL}{href}"

            # Location
            loc_el = card.select_one(".card-job__location")
            location = loc_el.get_text(separator=" ", strip=True) if loc_el else "New Zealand"
            # strip tag text like category links from location string
            if loc_el:
                location = " ".join(a.get_text(strip=True) for a in loc_el.select("a")) or location

            # Salary (use as snippet)
            salary_el = card.select_one(".card-job__salary")
            snippet = salary_el.get_text(strip=True) if salary_el else None

            # Classification
            class_el = card.select_one(".card-job__classification")
            category = class_el.get_text(strip=True) if class_el else ""

            job_id = hashlib.md5(full_url.encode()).hexdigest()[:12]
            jobs.append(JobResult(
                title=title,
                url=full_url,
                source=SOURCE,
                job_key=f"{SOURCE}:{job_id}",
                location=location,
                description_snippet=f"{category} | {snippet}" if snippet and category else (snippet or category or None),
            ))

        # Filter by keyword
        if kw_lower and jobs:
            filtered = [
                j for j in jobs
                if any(k in (j.title or "").lower() or k in (j.description_snippet or "").lower()
                       for k in kw_lower)
            ]
            jobs = filtered if filtered else jobs

        if not jobs:
            return ScrapeResult(
                source=SOURCE, display_name=DISPLAY_NAME,
                error="No matching listings found",
                search_url=url,
            )

        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME, jobs=jobs, search_url=url)

    except httpx.HTTPStatusError as e:
        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME,
                            error=f"HTTP {e.response.status_code}", search_url=url)
    except Exception as e:
        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME, error=str(e), search_url=url)
