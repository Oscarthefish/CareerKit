# CareerKit Local

A private, local-first CV and job-application assistant for cyber security professionals in New Zealand, built around a reusable **Master CV / career profile**.

You maintain your career history once — employers, skills, achievements, certifications, evidence — and CareerKit analyses that evidence against individual job descriptions to help you produce accurate, honestly-tailored applications. It runs entirely on your own machine against a local Ollama model. There is no cloud sync, no account, and no subscription.

```
Master Career Profile
        ↓
Job Description Analysis
        ↓
Evidence Matching  (Job Match, ATS, Recruiter Readiness)
        ↓
Recommendations  (gated by real evidence, never invented)
        ↓
Your Review
        ↓
Tailored / Custom CV
        ↓
Re-scan
        ↓
Export
```

The core principle behind every feature: **CareerKit should help you present genuine experience more effectively — it should never manufacture a better candidate.** Where a job asks for something your profile doesn't evidence, CareerKit is designed to surface that gap and ask you, not silently invent it.

---

## What's implemented

### Master CV / career profile
- Structured profile: work experience, skills (with aliases and confidence levels), certifications, training, achievements (STAR-style with measurable outcomes), projects, evidence items, and community involvement — not a single text blob.
- Generate a Master CV from that structured data at different confidentiality levels (public / recruiter-facing / CV-safe / full internal), and edit it manually.
- "Brutal Recruiter Review" — an AI critique of your current CV as a recruiter, hiring manager, HR screener and ATS would read it.
- Confidence levels (`confirmed_hands_on`, `working_knowledge`, `training_exposure`, `familiarity`, `unverified`, `do_not_include`) gate what AI-generated content is allowed to use — weak or unverified claims are excluded by default.

### Job applications
- Paste or upload a job description (PDF/DOCX/TXT/MD) and get structured analysis: required/preferred skills, hidden priorities, likely screening criteria, red flags.
- **Job Match** — an explainable 0–100% score with six sub-scores (hard skills, experience, qualifications, soft skills, industry context, job title), computed deterministically from evidence the AI classifies, not asked for as a raw percentage. Backed by a Requirement Coverage table (🟢 strong / 🟡 partial / 🔴 not demonstrated / ⚪ can't determine) and a Hard Skills table, using exact-match, known-synonym (SOC ≡ Security Operations Centre, SIEM ≡ Security Information and Event Management, etc.) and semantic matching in that order.
- **ATS Compatibility** — a deterministic 0–100% score. The content half genuinely inspects your CV text (headings, contact fields, dates, length, bullet structure). The document/export half reports what CareerKit's own PDF/DOCX exporters are built to guarantee (single column, standard fonts, no tables or images) rather than pretending to parse a rendered file it doesn't open. Includes "View what an ATS sees" — a plain-text rendering of your CV.
- **Recruiter Readiness** — a deterministic score built from the Brutal Review critique (first impression, credibility, achievement quality, readability, shortlisting risk), cached per CV version.
- **Priority Fixes**, each tagged with a Recommendation Safety tier:
  - `SAFE_OPTIMISATION` — your CV already evidences this; the fix is wording.
  - `EVIDENCE_NEEDED` — plausible, but unproven; CareerKit asks rather than adds it.
  - `DO_NOT_ADD` — a certification/qualification with no supporting evidence at all.
- **Custom CV Creation** — select which `SAFE_OPTIMISATION` fixes to apply (everything else stays locked until you add evidence), generate a CV with only those changes, then an automatic **before/after re-scan**. Job Match is not re-run here since it scores your structured data, not CV wording — that's deliberate, not a bug: a wording-only edit can't (and shouldn't) move that number.
- **Master CV Feedback Loop** — every "evidence needed" gap and every recurring gap across multiple applications comes with a "Have you done this?" prompt. Say yes and describe it, and it's added to your Master CV as new evidence, once, for every future application to benefit from.
- The original **Match Scorecard** (qualitative, LLM-only fit assessment), tailored **cover letters**, **CV adjustment notes** + **tailored CV**, **interview prep** packs (technical/behavioural/scenario questions, brush-up topics, a study plan), and a **LinkedIn** angle generator.
- Every application is saved as a full session folder of generated files (analysis, scorecard, cover letter, CV notes, interview prep, etc.), exportable to Markdown, DOCX and PDF.

### Job scanner
Scrapes NZ job boards (Seek, Hays, Absolute IT, Potentia, TradeMe) for saved search terms and lets you turn a listing straight into a new application.

### Speculative outreach (ReachOuts)
For companies you want to introduce yourself to even though they aren't advertising — separate from job applications, built around company research (which you or a browsing-capable assistant provide; the local model has no internet access) and generates an intro letter and angle.

### Experimental / in progress
- The Job Match engine's importance/evidence classification runs on your local model and, like any 8B-class model, is occasionally inconsistent — verify anything that looks off rather than trusting it blindly.
- CV generation currently renders new achievements by their title line rather than pulling in the fuller result/metric text — some detail you've recorded doesn't yet make it onto the rendered CV even though it's in your structured profile.

### Not built yet
- Web research for company/recruiter information (ReachOuts expects you to supply this)
- OCR for scanned (image-only) PDF CVs
- Interview recording transcription
- Salary benchmarking
- Multi-user support
- Browser extension for job scraping

---

## Accuracy and CV integrity

This is the load-bearing design principle of the whole app, not a slogan:

- The AI **classifies** evidence (importance, evidence level, title equivalence); CareerKit's own code **computes every score** from that classification. No score is ever "ask the model for a percentage."
- A generated cover letter, tailored CV or custom CV is checked after generation for fabricated years-of-experience claims, certifications stated as held when your profile marks them in-progress, and a former employer described as your current one — and is automatically rewritten if it slips through.
- The Custom CV generator can only apply a fix tagged `SAFE_OPTIMISATION` by the Job Match engine, checked server-side against the stored report — not by whatever a request claims.
- Nothing is added to your Master CV without you explicitly confirming it through the Feedback Loop.

None of this makes local-model output perfect. Review AI-generated content before you send it.

---

## Privacy — what actually happens to your data

- **AI processing is 100% local.** CareerKit talks to Ollama at `http://localhost:11434` by default. There is no Anthropic, OpenAI, or other external AI API key anywhere in this codebase — check `backend/app/ai/` yourself. Whatever you send to the local model (your profile, a job description, your CV) goes to the Ollama process running on your own machine and nowhere else.
- **No telemetry.** Nothing phones home. The GitHub Actions workflow in this repo only runs on pushes/PRs to this repository — it never touches your local data.
- **Job descriptions and CVs are not uploaded anywhere.** File uploads (PDF/DOCX job descriptions, example CVs) are parsed locally and stored in your local `data/` directory.
- **Everything personal lives under `data/`** (your SQLite database, generated CVs, application sessions, exports) and **`config/settings.json`** (your Ollama URL/model choice) — both are git-ignored. A fresh clone of this repository starts with an empty database; nothing here seeds your — or anyone's — real profile.
- **Job scanning** does make outbound HTTP requests, but only to the job boards you configure a search for (Seek, Hays, etc.) to fetch listings — the same as visiting them in a browser.
- **Back up `data/careerkit.db`** yourself if you want to keep your profile — it is the only copy and is deliberately not part of version control.

---

## Requirements

- Python 3.11 or later
- Node.js 20.9 or later
- Ollama running locally ([ollama.com](https://ollama.com))

---

## Setup

### 1. Install Ollama and pull a model

```bash
# Install from https://ollama.com
ollama serve
ollama pull llama3.1
```

`llama3.1` is the default model CareerKit is configured for — it has a large context window, which the Job Match, ATS and Recruiter Readiness prompts need. A smaller model (e.g. `llama3`) will work for simpler tasks but may truncate or produce unreliable results on the larger ones. For better quality across the board, if your hardware supports it:

```bash
ollama pull llama3.1:70b
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

CareerKit creates `config/settings.json` and the `data/` directory locally on first run. Both are git-ignored because they hold machine-specific paths, your CV, your job applications, and other personal information. To preconfigure settings before first run, copy `config/settings.example.json` to `config/settings.json`.

### 3. Set up the frontend

```bash
cd frontend
npm install
```

The frontend talks to the backend at `http://localhost:8000` by default. If you run the backend on a different port/host, copy `frontend/.env.example` to `frontend/.env.local` and adjust `NEXT_PUBLIC_API_URL`.

---

## Running

You need two terminals (or use `scripts/start-careerkit.sh`, which starts Ollama, the backend and the frontend together and opens the app in your browser).

### Terminal 1: Backend

```bash
cd backend
source venv/bin/activate        # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

The API runs at http://localhost:8000 — interactive docs at http://localhost:8000/docs

### Terminal 2: Frontend

```bash
cd frontend
npm run dev
```

The app runs at http://localhost:3000

---

## First run

1. Open http://localhost:3000 and complete the setup wizard.
2. Go to **Profile** and populate your work experience, skills, certifications and achievements — this is your Master CV's evidence base. There's nothing to import; you're the source of truth.
3. Go to **Master CV** and generate your CV from that profile. Run the **Master CV Health Check** (ATS Compatibility) and a **Brutal Recruiter Review** (Recruiter Readiness) to see where it stands before you apply anywhere.
4. Start a new **Application**, paste in a job description, and run **Job Analysis** then **Job Match**.
5. Review the Requirement Coverage table and Priority Fixes — pay attention to which ones are locked (`EVIDENCE_NEEDED` / `DO_NOT_ADD`) versus safe to action.
6. Where CareerKit asks "have you done this?" and the answer is yes, add it to your Master CV — every future application benefits from it.
7. Generate a Custom CV from the safe fixes, check the before/after re-scan, then generate your cover letter, interview prep and LinkedIn angle.
8. Export to Markdown, DOCX or PDF.

---

## Data storage

```
data/                       git-ignored - your data, never committed
  careerkit.db               SQLite database (profile, skills, jobs, scores, etc.)
  applications/               One folder per job application
    2026-06-01_Acme_SOC-Analyst/
      01-job-description.md
      02-job-analysis.md
      03-match-scorecard.md
      03b-job-match-report.md
      04-tailored-cover-letter.md
      05-cv-adjustment-notes.md
      05b-tailored-cv.md
      05c-custom-cv.md
      06-linkedin-angle.md
      07-recruiter-message.md
      08-interview-prep.md
      exports/                Exported DOCX and PDF files
  examples/                   Uploaded example CV analyses (style/structure only)
  exports/                    Master CV exports
  reachouts/                  Speculative-outreach session folders

config/
  settings.example.json      tracked - safe template (Ollama URL/model, no secrets)
  settings.json               git-ignored - your actual local settings

backend/app/
  api/                        FastAPI routes
  services/matching/          Job Match: requirement extraction, evidence, scoring, recommendations
  services/ats/                ATS Compatibility: CV parsing, checks, "what an ATS sees"
  services/recruiter/          Recruiter Readiness scoring
  services/insights/           Master CV Feedback Loop (cross-application gap detection)
  prompts/                     Every AI prompt template, as plain markdown files
  models/                      SQLAlchemy models (the actual data model)

backend/tests/                 Deterministic unit tests - no personal data, no LLM calls required
```

There is no `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` style secret anywhere in this project — CareerKit has nothing that needs a `.env` for credentials. `config/settings.json` is the equivalent for the one thing that IS configurable (which Ollama to talk to), and it's git-ignored the same way an `.env` would be.

---

## Testing

```bash
cd backend
venv/bin/python -m pytest -q
```

107 tests, all deterministic (no Ollama call required) — they exercise the scoring engine, evidence matching (including the anti-fabrication citation checks), ATS checks, recommendation safety, and skill-gap detection using synthetic fixtures, never real CV data.

Before publishing changes, also run:

```bash
cd backend && venv/bin/python -m compileall -q app
cd ../frontend && npm ci && npm run build
```

The GitHub Actions workflow runs the same backend import/test check and a Next.js build + route smoke-test on every push and pull request. Dependabot checks Python and npm packages weekly.

---

## Changing the AI model

Go to Settings in the app, or edit `config/settings.json`:

```json
{
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3.1",
  "ollama_num_ctx": 16384
}
```

- `llama3.1` (default) — large context window, needed for Job Match/ATS/Recruiter Readiness prompts.
- `llama3.1:70b` — better quality, slower, needs considerably more RAM.
- `llama3`, `mistral`, `phi3` — will work for simpler generation (cover letters, interview prep) but may truncate or produce unreliable JSON on the larger analysis prompts; lower `ollama_num_ctx` accordingly if you switch to one of these and hit memory limits, but don't go below ~12,288 or the Job Match/ATS prompts will start truncating.

---

## Supported file formats

Upload job descriptions and example CVs as PDF (text-based, not scanned), Word DOCX, plain text, or Markdown.

---

## Writing principles

CareerKit enforces these rules in AI prompts, and checks the more easily-gamed ones (banned phrases, fixed year-counts, held-vs-in-progress certifications, current-vs-former employers) programmatically after generation rather than trusting the model alone:

- No em dashes
- No generic AI phrases ("excited to apply", "passionate about", "leverage", "synergy")
- No keyword stuffing
- No invented experience, certifications, or metrics
- British / New Zealand English throughout
- Direct, professional, human language

---

## Limitations

- CareerKit's Job Match score is its own internal estimate. It is **not** the score a real employer's ATS would produce — different ATS products parse and weight CVs very differently, and CareerKit cannot see inside them.
- A high Job Match, ATS, or Recruiter Readiness score does not guarantee an interview. Aim for accurate, relevant alignment, not a maximised number.
- ATS document/export checks describe what CareerKit's own exporters are built to produce — they do not parse a rendered PDF/DOCX the way a third-party ATS might.
- Semantic and importance classification run on your local model and can occasionally misjudge — review before trusting.
- Job-title equivalence (e.g. "Senior Security Operations Analyst" ≈ "Senior SOC Analyst") is an interpretation CareerKit offers as a suggestion, never a rewrite of your real title — check it makes sense for the specific role.
- Exported DOCX/PDF formatting may render slightly differently across viewers/versions of Word.
- CareerKit cannot confirm experience that isn't in your Master CV — that's by design, not a gap to work around by adding more data it can't verify.

---

## Security

- Never commit `.env`, `.env.local`, or `config/settings.json` — they're git-ignored for you, but double-check `git status` before committing if you ever move where local config lives.
- Use `.env.example` / `config/settings.example.json` as the templates for anything that needs configuring.
- This project has no API keys to rotate today (no external AI provider is used), but if that ever changes for you locally, treat any credential that was ever committed as compromised and rotate it, even after removing it — deleting a file doesn't remove it from earlier commits.
- Review generated exports (cover letters, tailored/custom CVs) before sharing them externally — they can contain achievement detail you may want to phrase differently outside CareerKit's own review flow.
- Before pushing to a public fork or remote, see the next section.

---

## Privacy check before pushing

Run this from the repository root before any `git push`:

```bash
./scripts/privacy-check.sh
```

It fails (non-zero exit) if it finds: a tracked `.env*` file (other than `.env.example`), a tracked database/SQLite file, a tracked PDF/DOCX outside of docs you've deliberately allowed, anything under `data/` besides `.gitkeep`, or an obvious secret pattern (API-key-shaped strings, `password =`, etc.) in a tracked file. It is intentionally simple — a first line of defence, not a substitute for reading `git status` and `git diff` yourself before you push.

---

## Troubleshooting

**Ollama is not connecting**
- Make sure Ollama is running: `ollama serve`
- Check the URL in Settings (default: http://localhost:11434)

**Model not found**
- Pull the model: `ollama pull llama3.1`
- Check the model name in Settings matches what you pulled

**Job Match / ATS / Recruiter Readiness generation fails or returns an error**
- These prompts need a reasonably large context window. Try a larger model, or check `ollama_num_ctx` in Settings hasn't been set too low.

**PDF upload fails**
- Only text-based PDFs are supported (not scanned images)
- Try converting to text or DOCX first

**Frontend cannot reach backend**
- Make sure the backend is running on port 8000
- Check for CORS errors in the browser console
- The frontend expects the API at http://localhost:8000 by default (`frontend/.env.example`)

**Generation is slow**
- Larger models and larger prompts (Job Match, ATS, Recruiter Readiness) take longer, especially on CPU-only hardware. Try a smaller model for faster iteration, at the cost of reliability on the bigger analysis prompts.
- Make sure no other applications are using GPU/memory heavily.

---

CareerKit is released under the [MIT License](LICENSE).
