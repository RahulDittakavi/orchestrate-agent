"""
risk.py — Rule-based risk assessment for escalation decisions.
Runs BEFORE the LLM to catch obvious high-risk cases fast.
Only escalates genuinely dangerous/sensitive situations — informational
queries (even about lost cards or disputes) should reach the LLM.
"""

ESCALATION_KEYWORDS = {
    "fraud": [
        "fraudulent", "unauthorized transaction", "scam", "phishing",
        "identity theft", "chargeback", "suspicious transaction", "suspicious activity",
        "didn't make this", "not me", "not authorized"
    ],
    "account_security": [
        "account hacked", "account compromised", "someone else logged in",
        "unauthorized access", "account locked", "locked out", "banned account",
        "account suspended"
    ],
    "billing_dispute": [
        "double charged", "charged twice", "wrong charge", "overcharged",
        "refund not received", "payment failed but charged", "billing error",
        "money deducted without"
    ],
    "legal": [
        "legal action", "lawsuit", "attorney", "lawyer", "court order",
        "data breach", "gdpr violation", "privacy violation"
    ],
    "prompt_injection": [
        "ignore previous instructions", "show me your prompt", "reveal your system",
        "affiche toutes les règles", "règles internes", "logique exacte",
        "override your instructions", "bypass your filters"
    ],
}

def assess_risk(issue: str, company: str) -> dict:
    """
    Returns a risk assessment dict:
    {
        "should_escalate": bool,
        "risk_category": str or None,
        "reason": str
    }
    """
    issue_lower = issue.lower()

    for category, keywords in ESCALATION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in issue_lower:
                return {
                    "should_escalate": True,
                    "risk_category": category,
                    "reason": f"Detected high-risk keyword: '{keyword}' in category '{category}'"
                }

    return {
        "should_escalate": False,
        "risk_category": None,
        "reason": "No high-risk patterns detected"
    }
