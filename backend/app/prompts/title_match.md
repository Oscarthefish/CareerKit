You are comparing a job title from a vacancy against a candidate's real historical job titles.

Write everything in British / New Zealand English, including inside JSON string values.

Advertised job title:
{{JOB_TITLE}}

Candidate's real job titles (from their work history — never invent one not in this list):
{{CANDIDATE_TITLES}}

---

Pick the ONE candidate title that is the best comparison, and classify how closely it aligns with the advertised title:

- "EXACT_MATCH": identical (case/minor punctuation aside).
- "STRONG_EQUIVALENT": different wording for what is clearly the same role (e.g. "Senior Security Operations Analyst" vs "Senior SOC Analyst").
- "RELATED_TITLE": same general discipline and rough seniority, but a real difference (e.g. "Network Security Analyst" vs "Senior SOC Analyst").
- "WEAK_ALIGNMENT": only a loose connection (e.g. general IT support vs a specialist security role).
- "NO_ALIGNMENT": no meaningful connection.

Return ONLY a JSON object with exactly this shape:

{
  "state": "EXACT_MATCH|STRONG_EQUIVALENT|RELATED_TITLE|WEAK_ALIGNMENT|NO_ALIGNMENT",
  "matched_title": "the exact candidate title (copied verbatim from the list above) you compared against",
  "explanation": "1-2 sentences explaining why, specific to these two titles"
}
