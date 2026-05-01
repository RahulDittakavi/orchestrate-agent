"""
risk.py — Rule-based risk assessment for escalation decisions.
Runs BEFORE the LLM to catch obvious high-risk cases fast.
"""

# Keywords that should trigger immediate escalation
ESCALATION_KEYWORDS = {
    "fraud": [
        "fraud", "fraudulent", "unauthorized", "scam", "stolen", "hacked",
        "compromised", "phishing", "identity theft", "dispute", "chargeback",
        "not me", "didn't make this", "suspicious transaction", "suspicious activity"
    ],
    "account_security": [
        "can't log in", "cannot login", "locked out", "account locked",
        "password reset not working", "account suspended", "banned account",
        "account compromised", "someone else logged in", "unauthorized access"
    ],
    "billing_dispute": [
        "double charged", "wrong charge", "overcharged", "refund not received",
        "payment failed but charged", "charged twice", "billing error",
        "money deducted", "amount debited"
    ],
    "legal": [
        "legal action", "lawsuit", "attorney", "lawyer", "court",
        "gdpr", "data breach", "privacy violation", "compliance"
    ],
    "sensitive_visa": [
        "card stolen", "lost card", "block my card", "freeze card",
        "card fraud", "atm fraud", "pos fraud", "international transaction blocked"
    ]
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

    # Visa-specific: any payment/transaction issue is higher risk
    if company == "Visa":
        payment_keywords = ["transaction", "payment", "transfer", "amount", "money", "card"]
        for kw in payment_keywords:
            if kw in issue_lower:
                return {
                    "should_escalate": True,
                    "risk_category": "payment_sensitive",
                    "reason": f"Visa payment-related issue detected — routing to human for safety"
                }

    return {
        "should_escalate": False,
        "risk_category": None,
        "reason": "No high-risk patterns detected"
    }
