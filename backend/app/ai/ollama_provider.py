import json
import re
import httpx
from typing import Optional
from .base import AIProvider

# Prepended to every system prompt. Local 8B models routinely drop style rules
# that live in the middle of a long user prompt, so the language rule is stated
# here, first, and unconditionally.
STYLE_SYSTEM = (
    "Always write in British / New Zealand English. Never use American spellings. "
    "Use -ise / -isation (organise, prioritise, specialise, analyse), "
    "-our (colour, behaviour, favour, honour), -re (centre, metre), "
    "and 'licence', 'defence', 'programme', 'catalogue', 'grey', 'fulfil', "
    "'travelled', 'modelling', 'artefact'. "
    "This applies to every word you output, including inside JSON string values."
)


def _find_banned_violations(text: str, banned_phrases: list[str]) -> list[str]:
    """Case-insensitive substring check against the banned-phrase list. Entries
    with a conditional exception (e.g. "proven track record (unless...)") are
    skipped here — those need judgement a substring match can't apply, so they
    stay instruction-only rather than triggering an automatic retry."""
    lowered = text.lower()
    found = []
    for phrase in banned_phrases:
        if "(unless" in phrase:
            continue
        bare = phrase.split(" (")[0].strip()
        if bare and bare.lower() in lowered:
            found.append(bare)
    return found


# A hardcoded "X years of experience" figure is told not to appear (prompts ask
# for anchor dates like "since 2014" instead, since a fixed count goes stale and
# is easy to get wrong), but the model keeps writing one anyway with whatever
# number sounds plausible. A literal phrase ban can't catch this since the
# number varies every time, so it needs its own pattern.
_YEARS_EXPERIENCE_PATTERN = re.compile(
    r"\b(?:over|more than|almost|nearly|around|approximately)?\s*\d{1,2}\+?\s*years?"
    r"(?:'|\s)*\s*(?:of\s+)?experience\b",
    re.IGNORECASE,
)


def _find_years_experience_claims(text: str) -> list[str]:
    return [m.group(0) for m in _YEARS_EXPERIENCE_PATTERN.finditer(text)]


_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CERT_QUALIFIERS = ("in progress", "in-progress", "studying", "working towards",
                     "pursuing", "currently completing", "underway", "candidate for")


def _find_in_progress_cert_claims(text: str, in_progress_certs: list[str]) -> list[str]:
    """The profile marks a certification in_progress=True (not yet obtained), but
    a model routinely still writes "As a <cert>, I have..." as if it were held.
    Flag any sentence naming the cert (by full name or its bracketed abbreviation)
    that doesn't also carry a qualifying phrase."""
    if not in_progress_certs:
        return []
    sentences = _SENTENCE_SPLIT.split(text)
    found = []
    for cert in in_progress_certs:
        names = {cert, cert.split(" (")[0].strip()}
        m = re.search(r"\(([A-Z0-9]{2,10})\)", cert)
        if m:
            names.add(m.group(1))
        names.discard("")
        for sentence in sentences:
            low = sentence.lower()
            if any(n.lower() in low for n in names) and not any(q in low for q in _CERT_QUALIFIERS):
                found.append(cert)
                break
    return found


def _find_current_employer_mismatch(text: str, former_employers: list[str]) -> list[str]:
    """The profile marks is_current=False for a former employer (e.g. after a
    redundancy), but a model routinely still writes "my current role at X"."""
    if not former_employers:
        return []
    sentences = _SENTENCE_SPLIT.split(text)
    found = []
    for employer in former_employers:
        for sentence in sentences:
            low = sentence.lower()
            if employer.lower() in low and ("current" in low or "currently" in low):
                found.append(employer)
                break
    return found


class OllamaProvider(AIProvider):

    def __init__(self, base_url: str, model: str, num_ctx: int = 16384):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.num_ctx = num_ctx
        self.timeout = 300.0

    def _system(self, system: Optional[str]) -> str:
        return f"{STYLE_SYSTEM}\n\n{system}".strip() if system else STYLE_SYSTEM

    async def _chat(self, messages: list[dict], temperature: float = 0.7) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": self.num_ctx,
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        banned_phrases: Optional[list[str]] = None,
        flag_years_experience: bool = False,
        in_progress_certs: Optional[list[str]] = None,
        former_employers: Optional[list[str]] = None,
    ) -> str:
        # Every prompt template opens with persona/instruction framing
        # ("You are a senior CV writer..."). Smaller local models treat that as
        # something to reply to when it arrives as a user message ("I see
        # you're a..."), rather than as instructions to follow. Putting the
        # whole thing in the system role and giving the model a minimal,
        # separate user turn to act on keeps it from responding conversationally.
        messages = [
            {"role": "system", "content": f"{self._system(system)}\n\n{prompt}"},
            {"role": "user", "content": (
                "Produce the output now, following the instructions above exactly. "
                "Do not include any preamble, explanation, acknowledgement, or "
                "conversational text - output ONLY the requested content, starting "
                "immediately with it."
            )},
        ]
        content = await self._chat(messages)

        # A small local model will restate an instruction like "never use X"
        # right back in the prompt and still write X anyway — telling it not to
        # do something is not reliable for free-form prose. Catching it after
        # the fact and forcing one corrective rewrite works far better than
        # any amount of extra wording in the instruction itself.
        violations = list(_find_banned_violations(content, banned_phrases)) if banned_phrases else []
        year_violations = _find_years_experience_claims(content) if flag_years_experience else []
        cert_violations = _find_in_progress_cert_claims(content, in_progress_certs or [])
        employer_violations = _find_current_employer_mismatch(content, former_employers or [])

        if violations or year_violations or cert_violations or employer_violations:
            note = ""
            if violations:
                note += (
                    "Your response used phrase(s) you were explicitly told never to use: "
                    + ", ".join(f'"{v}"' for v in violations) + ". "
                )
            if year_violations:
                note += (
                    "Your response also stated a fixed year-count of experience ("
                    + ", ".join(f'"{v}"' for v in year_violations) + ") — you were told to "
                    "anchor experience to actual dates from the profile (e.g. \"since 2014\") "
                    "instead of a fixed number, since a fixed count is often wrong and goes "
                    "stale. Remove the year-count entirely and use an anchor date instead. "
                )
            if cert_violations:
                note += (
                    "Your response named the following certification(s) as if already held, "
                    "but the profile marks them as NOT YET OBTAINED (in progress): "
                    + ", ".join(f'"{v}"' for v in cert_violations) + ". Either remove the claim "
                    "entirely, or if it is genuinely relevant, state clearly that the candidate "
                    "is currently studying towards / working towards it — never imply it is held. "
                )
            if employer_violations:
                note += (
                    "Your response described the following employer(s) as the candidate's "
                    "CURRENT role, but the profile marks them as a FORMER employer (not current): "
                    + ", ".join(f'"{v}"' for v in employer_violations) + ". Rewrite using past "
                    "tense for that role (e.g. \"held the role of ... at ...\" or \"from ... to "
                    "...\") — never describe it as current. "
                )
            note += (
                "Rewrite your FULL response from scratch fixing this, expressing the same "
                "meaning in different, natural words. Output ONLY the corrected content, "
                "nothing else."
            )
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": note})
            content = await self._chat(messages)

        return content

    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        required_keys: Optional[list[str]] = None,
    ) -> dict:
        json_system = (
            self._system(system)
            + "\n\nYou must respond with valid JSON only. No explanation, no markdown "
            "fences, just the raw JSON object. Use exactly the field names requested "
            "in the prompt and no others."
        )

        last_error: Optional[Exception] = None
        for attempt in range(2):
            messages = [
                {"role": "system", "content": json_system},
                {"role": "user", "content": prompt},
            ]
            if attempt > 0:
                messages.append({
                    "role": "user",
                    "content": (
                        "Your previous response did not match the requested schema. "
                        "Return ONLY a JSON object with these top-level keys: "
                        + ", ".join(required_keys or [])
                        + ". Do not echo the input back."
                    ),
                })

            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.3,
                    "num_ctx": self.num_ctx,
                },
            }

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                data = response.json()
                content = data["message"]["content"]

            content = re.sub(r"^```(?:json)?\s*", "", content.strip())
            content = re.sub(r"\s*```$", "", content.strip())

            try:
                parsed = json.loads(content)
            except json.JSONDecodeError as e:
                last_error = e
                continue

            if required_keys and not _has_keys(parsed, required_keys):
                last_error = ValueError(
                    f"model response missing required keys {required_keys}; "
                    f"got {list(parsed) if isinstance(parsed, dict) else type(parsed).__name__}"
                )
                continue

            return parsed

        raise ValueError(f"model did not return usable JSON: {last_error}")

    async def health_check(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"] for m in data.get("models", [])]
                    model_available = any(
                        m == self.model or m.startswith(self.model + ":") for m in models
                    )
                    return {
                        "status": "ok",
                        "url": self.base_url,
                        "model": self.model,
                        "model_available": model_available,
                        "available_models": models,
                    }
        except httpx.ConnectError:
            return {
                "status": "error",
                "message": f"Cannot connect to Ollama at {self.base_url}. Run: ollama serve",
                "url": self.base_url,
                "model": self.model,
                "model_available": False,
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": self.base_url,
                "model": self.model,
                "model_available": False,
            }


def _has_keys(parsed, required_keys: list[str]) -> bool:
    if not isinstance(parsed, dict):
        return False
    return any(k in parsed for k in required_keys)
