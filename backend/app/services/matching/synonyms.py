"""Deterministic concept-equivalence table for cyber security terminology.

Exact keyword matching alone misses genuinely equivalent evidence (a CV that
says "Splunk" should count as evidence for a JD asking for "SIEM"). This table
gives the evidence matcher a fixed, auditable set of equivalences to check
before ever falling back to an LLM judgement call — same input always produces
the same match, and every group here is something a security professional
would recognise as a plain synonym or acronym expansion, not a semantic leap.

Not exhaustive by design: a term missing from this table simply falls through
to the LLM-assisted pass in evidence.py rather than being silently unmatched.
"""

SYNONYM_GROUPS: list[set[str]] = [
    {"soc", "security operations centre", "security operations center", "security operations"},
    {"siem", "security information and event management"},
    {"edr", "endpoint detection and response"},
    {"xdr", "extended detection and response"},
    {"mdr", "managed detection and response"},
    {"ir", "incident response", "incident handling", "incident management"},
    {"vulnerability management", "vulnerability assessment", "vuln management", "vulnerability scanning"},
    {"soar", "security orchestration automation and response",
     "security orchestration, automation and response", "security orchestration and automation"},
    {"osint", "open source intelligence", "open-source intelligence"},
    {"threat hunting", "threat hunt", "proactive threat hunting"},
    {"threat intelligence", "cti", "cyber threat intelligence"},
    {"dlp", "data loss prevention"},
    {"iam", "identity and access management"},
    {"pam", "privileged access management"},
    {"mfa", "multi-factor authentication", "multi factor authentication", "two-factor authentication", "2fa"},
    {"pentest", "penetration testing", "pen testing", "pen test", "pen-testing"},
    {"vapt", "vulnerability assessment and penetration testing"},
    {"ndr", "network detection and response"},
    {"ips", "intrusion prevention system", "intrusion prevention"},
    {"ids", "intrusion detection system", "intrusion detection"},
    {"waf", "web application firewall"},
    {"casb", "cloud access security broker"},
    {"cspm", "cloud security posture management"},
    {"grc", "governance risk and compliance", "governance, risk and compliance", "governance risk compliance"},
    {"phishing simulation", "phishing awareness", "phishing testing"},
    {"digital forensics", "computer forensics", "forensic investigation", "dfir"},
    {"malware analysis", "malware reverse engineering", "reverse engineering malware"},
    {"soc analyst", "security operations analyst", "security analyst"},
]

_LOOKUP: dict[str, set[str]] = {}
for _group in SYNONYM_GROUPS:
    for _term in _group:
        _LOOKUP[_term] = _group


def expand_terms(term: str) -> set[str]:
    """All known-equivalent lowercase phrasings for `term`, including itself."""
    low = (term or "").strip().lower()
    if not low:
        return set()
    return set(_LOOKUP.get(low, set())) | {low}
