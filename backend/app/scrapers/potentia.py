import re
import httpx
from bs4 import BeautifulSoup
from .base import JobResult, ScrapeResult, HEADERS

DISPLAY_NAME = "Potentia"
SOURCE = "potentia"
BASE_URL = "https://potentia.co.nz"
JOBS_URL = f"{BASE_URL}/jobs"


async def scrape(keywords: str) -> ScrapeResult:
    kw_lower = {k.lower() for k in keywords.split()}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(JOBS_URL, headers=HEADERS)
            r.raise_for_status()

        soup = BeautifulSoup(r.text, "lxml")
        jobs = []

        for card in soup.select(".jCard"):
            title_el = card.select_one(".jCardHeader")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            if not title or len(title) < 3:
                continue

            # Job ID from the onclick: $('#f_60190322').submit()
            onclick = card.get("onclick", "")
            job_id_match = re.search(r"f_(\d+)", onclick)
            if not job_id_match:
                continue
            job_id = job_id_match.group(1)

            # Find the /job/ link for this card
            job_link = card.select_one(f"a[href*='/job/{job_id}']") or card.select_one("a[href*='/job/']")
            if job_link:
                href = job_link.get("href", "")
                full_url = href if href.startswith("http") else f"{BASE_URL}{href}"
            else:
                # Construct from slug in data-cardtext
                full_url = f"{BASE_URL}/job/{job_id}-{_slugify(title)}"

            location = card.get("data-location") or "New Zealand"
            job_type = card.get("data-jobtype", "")
            specialty = card.select_one(".jSpecialty")
            salary = card.select_one(".jSalary")
            posted = card.select_one(".jPostedTime")
            bullets = [li.get_text(strip=True) for li in card.select(".jBullets li")]

            snippet_parts = []
            if specialty:
                snippet_parts.append(specialty.get_text(strip=True))
            if salary:
                snippet_parts.append(salary.get_text(strip=True))
            if bullets:
                snippet_parts.append(" | ".join(bullets[:2]))
            if job_type:
                snippet_parts.append(job_type)

            jobs.append(JobResult(
                title=title,
                url=full_url,
                source=SOURCE,
                job_key=f"{SOURCE}:{job_id}",
                location=location,
                description_snippet=" | ".join(snippet_parts)[:400] if snippet_parts else None,
                date_posted=posted.get_text(strip=True) if posted else None,
            ))

        # Filter by keyword
        if kw_lower and jobs:
            filtered = [
                j for j in jobs
                if any(
                    k in (j.title or "").lower()
                    or k in (j.description_snippet or "").lower()
                    or k in (j.location or "").lower()
                    for k in kw_lower
                )
            ]
            jobs = filtered if filtered else jobs

        if not jobs:
            return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME,
                                error="No listings found on jobs page", search_url=JOBS_URL)

        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME, jobs=jobs, search_url=JOBS_URL)

    except httpx.HTTPStatusError as e:
        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME,
                            error=f"HTTP {e.response.status_code}", search_url=JOBS_URL)
    except Exception as e:
        return ScrapeResult(source=SOURCE, display_name=DISPLAY_NAME, error=str(e), search_url=JOBS_URL)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
