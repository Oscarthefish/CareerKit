You are checking a candidate's Master CV profile for evidence of specific job requirements.

Write everything in British / New Zealand English, including inside JSON string values.

Requirements to check (these could not be resolved by an exact keyword/synonym search, so look for indirect or paraphrased evidence):
{{REQUIREMENTS}}

Candidate Profile:
{{PROFILE_SUMMARY}}

---

For each requirement, decide whether the candidate profile above provides evidence of it. Look for genuine semantic evidence, not just exact wording — for example, a profile that says "Investigated alerts using Splunk and Cortex XDR" IS evidence for a requirement called "SIEM investigation experience", because Splunk is a SIEM platform, even though the word "SIEM" never appears.

RULES — these are strict:
- Classify each requirement as exactly one of: EXPLICIT (the profile directly names this or an unambiguous synonym), INFERRED (the profile shows something that reasonably implies it without naming it), POSSIBLE (weak/indirect signal only), or NOT_FOUND (nothing supports it).
- For EXPLICIT or INFERRED, you MUST cite the specific profile item(s) that support it in "sources" — name the real skill, achievement, employer/role, certification, training or project exactly as it appears in the profile above. A source that does not correspond to a real, named item in the profile is not acceptable.
- NEVER cite a certification or training item whose status is "in progress" as evidence that something is held or demonstrated — that can support POSSIBLE at most.
- NEVER use the requirement's own wording restated as if it were evidence. If you cannot point to a specific profile item, the answer is NOT_FOUND, not EXPLICIT.
- If genuinely nothing supports a requirement, say NOT_FOUND. Do not stretch an unrelated item to make a match — a general information-security background does not, by itself, evidence a specific NAMED skill, tool, or business domain (e.g. a SOC analyst background is not, by itself, evidence of "fraud intelligence" or "insurance claims management" - those are specific domains that need their own direct evidence).
- The strictness above is about specific named things (a product, a certification, a niche domain), not broad competencies. A requirement phrased as a general competency ("analytical skills", "investigations skills", "process improvement", "stakeholder engagement", "communication") should be classified as INFERRED when the profile shows concrete work that plainly demonstrates it, even without using that exact phrase — e.g. "led containment and investigation during a major incident, then delivered the post-incident review to leadership" is real INFERRED evidence for "investigations skills", "analytical skills", and "stakeholder engagement" all at once. Still cite the specific achievement/role you drew it from - the bar is a real, named source, not the exact wording.

Return ONLY a JSON object with exactly this shape:

{
  "evidence": [
    {
      "requirement": "the exact requirement name as given above",
      "evidence_level": "EXPLICIT|INFERRED|POSSIBLE|NOT_FOUND",
      "confidence": 0.0,
      "sources": ["specific profile item(s), only for EXPLICIT/INFERRED"],
      "rationale": "one sentence explaining the classification"
    }
  ]
}

Include exactly one entry per requirement listed above, in the same order.
