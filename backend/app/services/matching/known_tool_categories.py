"""A small, deliberately incomplete lookup of well-known SOC/security-
operations product names to their broad category - used only to pair a
job-description-named tool the candidate doesn't have with a real tool the
candidate DOES have in the same category, for the cover letter's tool/
platform gap bridge (see applications.py's _ensure_tool_gap_bridge_mentioned).
A vendor not listed here is simply never bridged, never guessed at - this
table only ever adds a bridge when it's confident of the category, it
never asserts one.

Category strings deliberately match this project's own tool_category
vocabulary (see profile_service.py's _TOOL_FUNCTIONAL_GROUPS source tags),
so a lookup hit can be compared directly against a candidate's own
skill.tool_category value without any further translation."""

KNOWN_TOOL_CATEGORIES: dict[str, str] = {
    # SIEM
    "sentinel": "SIEM", "splunk": "SIEM", "qradar": "SIEM", "logrhythm": "SIEM",
    "rapid7": "SIEM", "insightidr": "SIEM", "arcsight": "SIEM", "chronicle": "SIEM",
    "sumo logic": "SIEM", "elastic security": "SIEM", "devo": "SIEM", "exabeam": "SIEM",
    "securonix": "SIEM", "graylog": "SIEM",
    # EDR / XDR
    "crowdstrike": "EDR / XDR", "falcon": "EDR / XDR", "sentinelone": "EDR / XDR",
    "carbon black": "EDR / XDR", "cortex xdr": "EDR / XDR", "defender for endpoint": "EDR / XDR",
    "trellix": "EDR / XDR", "sophos intercept x": "EDR / XDR", "cybereason": "EDR / XDR",
    "cisco amp": "EDR / XDR", "cisco secure endpoint": "EDR / XDR",
    # Firewalls
    "fortinet": "Firewalls", "fortigate": "Firewalls", "palo alto": "Firewalls",
    "checkpoint": "Firewalls", "check point": "Firewalls", "cisco asa": "Firewalls", "pfsense": "Firewalls",
    # Case management / ticketing
    "servicenow": "Case Management", "jira service management": "Case Management",
    "zendesk": "Case Management", "freshservice": "Case Management",
}


def known_category_for(text: str) -> str | None:
    """Longest-match lookup: checks longer, more specific vendor names
    before shorter ones (e.g. "cortex xdr" before any shorter overlap),
    so a multi-word product name isn't accidentally matched by a shorter,
    coincidental substring elsewhere in the lookup."""
    low = (text or "").lower()
    for name in sorted(KNOWN_TOOL_CATEGORIES, key=len, reverse=True):
        if name in low:
            return KNOWN_TOOL_CATEGORIES[name]
    return None
