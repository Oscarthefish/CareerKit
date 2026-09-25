# CareerKit Local

A private, local-only job application assistant for cyber security professionals in New Zealand.

All data stays on your machine. No cloud sync, no accounts, no subscriptions.

---

## What it does

- Builds and maintains a master profile (CV, skills, achievements, evidence)
- Analyses job descriptions to extract requirements, keywords, and hidden priorities
- Produces a match scorecard comparing your profile to the role
- Generates tailored cover letters in NZ professional tone
- Produces CV adjustment notes for each role (without rewriting the whole CV)
- Generates interview preparation packs with STAR prompts
- Builds LinkedIn content from your profile
- Saves every application session as a complete folder of files
- Exports to Markdown, Word DOCX, and PDF

AI runs locally via Ollama. No data leaves your machine.

---

## Requirements

- Python 3.11 or later
- Node.js 20.9 or later
- Ollama running locally (ollama.com)

---

## Setup

### 1. Install Ollama and pull a model

```bash
# Install from https://ollama.com
ollama serve
ollama pull llama3
```

For better results on complex tasks, use a larger model:
```bash
ollama pull llama3:70b
```

### 2. Set up the backend

```bash
cd careerkit-local/backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

CareerKit creates `config/settings.json` and the `data/` directory locally. Both
are intentionally excluded from Git because they can contain machine-specific
paths, CVs, job applications, and other personal information. To preconfigure
settings, copy `config/settings.example.json` to `config/settings.json`.

### 3. Set up the frontend

```bash
cd careerkit-local/frontend
npm install
```

---

## Running

You need two terminals.

### Terminal 1: Backend

```bash
cd careerkit-local/backend
source venv/bin/activate        # Windows: venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

The API runs at http://localhost:8000
API docs available at http://localhost:8000/docs

### Terminal 2: Frontend

```bash
cd careerkit-local/frontend
npm run dev
```

The app runs at http://localhost:3000

Open http://localhost:3000 in your browser and complete the setup wizard.

---

## First run

1. Open http://localhost:3000
2. Complete the setup wizard (about 10 minutes)
3. Go to Master CV and generate your CV
4. Start a new job application from the Applications page

---

## Data storage

```
data/
  careerkit.db          SQLite database (profile, skills, jobs, etc.)
  applications/         One folder per job application
    2024-06-01_Acme_SOC-Analyst/
      01-job-description.md
      02-job-analysis.md
      03-match-scorecard.md
      04-tailored-cover-letter.md
      05-cv-adjustment-notes.md
      06-linkedin-angle.md
      07-recruiter-message.md
      08-interview-prep.md
      ...
      exports/          Exported DOCX and PDF files
  examples/             Uploaded example CV analyses
  exports/              Master CV exports
  profile/              Reserved for future use
```

The contents of `data/` are private runtime data and must not be committed.

---

## Repository checks

The GitHub Actions workflow checks that the Python backend imports successfully
and runs its tests, then builds Next.js and smoke-tests every primary application
route on every push and pull request. Dependabot checks Python and npm packages
weekly.

Before publishing changes, run:

```bash
cd backend
venv/bin/python -m compileall -q app

cd ../frontend
npm ci
npm run build
```

CareerKit is released under the [MIT License](LICENSE).

---

## Changing the AI model

Go to Settings in the app, or edit `config/settings.json`:

```json
{
  "ollama_url": "http://localhost:11434",
  "ollama_model": "llama3"
}
```

Recommended models:
- `llama3` or `llama3:8b` - Fast, good for most tasks
- `llama3:70b` - Better quality, slower, needs more RAM (40GB+)
- `mistral` - Good alternative, fast
- `phi3` - Small and fast, less accurate

---

## Supported file formats

Upload job descriptions and example CVs as:
- PDF (text-based, not scanned)
- Word DOCX
- Plain text TXT
- Markdown MD

---

## Writing principles

CareerKit enforces these rules in all AI prompts:

- No em dashes
- No generic AI phrases (excited to apply, passionate about, leverage, synergy)
- No keyword stuffing
- No invented experience
- Direct, professional, human language
- NZ professional tone
- ATS-friendly structure with human readability

---

## Confidence levels

Every skill, achievement, and evidence item has a confidence level:

- **Confirmed** - You have direct, demonstrable experience
- **Inferred** - Reasonable to claim based on related experience
- **Weak** - Marginal claim that needs careful framing
- **Do not use** - Should not appear in any application

Only confirmed and inferred items are included in AI-generated content by default.

---

## Phase 2 ideas (not built yet)

- Web research for company and recruiter information
- OCR for scanned PDF CVs
- Interview recording transcription
- Salary benchmarking
- Multi-user support
- Browser extension for job scraping

---

## Troubleshooting

**Ollama is not connecting**
- Make sure Ollama is running: `ollama serve`
- Check the URL in Settings (default: http://localhost:11434)

**Model not found**
- Pull the model: `ollama pull llama3`
- Check the model name in Settings matches what you pulled

**PDF upload fails**
- Only text-based PDFs are supported (not scanned images)
- Try converting to text or DOCX first

**Frontend cannot reach backend**
- Make sure the backend is running on port 8000
- Check for CORS errors in the browser console
- The frontend expects the API at http://localhost:8000

**Generation is slow**
- Larger models take longer. Try `llama3:8b` or `mistral` for speed.
- Make sure no other applications are using GPU/memory heavily.
