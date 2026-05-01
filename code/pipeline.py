"""
pipeline.py — Core triage pipeline. Orchestrates all components.
"""

import json
import re
import time
from google import genai
from google.genai import types
from prompts import TRIAGE_PROMPT, DOMAIN_CLASSIFIER_PROMPT
from retriever import Retriever
from risk import assess_risk

GEMINI_MODEL = "gemini-2.5-flash"

# Fallback escalation response template
ESCALATION_RESPONSE = (
    "Thank you for reaching out. Your request has been escalated to our support team "
    "as it requires specialized assistance. A human agent will contact you shortly. "
    "We apologize for any inconvenience."
)

OUT_OF_SCOPE_RESPONSE = (
    "Thank you for contacting support. Unfortunately, this request appears to be outside "
    "the scope of our support services. If you believe this is an error, please rephrase "
    "your issue or contact the appropriate support channel."
)

class TriagePipeline:
    def __init__(self, gemini_api_key: str):
        self.client = genai.Client(api_key=gemini_api_key)
        self.retriever = Retriever()
        print(f"[✓] Pipeline initialized (model: {GEMINI_MODEL})")

    # Seconds to sleep after every successful Gemini call to stay under free-tier RPM limit.
    # Free tier = 5 req/min → 1 call per 12s minimum; 13s gives a safe buffer.
    _RATE_LIMIT_SLEEP = 13

    def _call_gemini(self, prompt: str, max_retries: int = 3) -> str:
        """Call Gemini. Sleeps after each call to respect free-tier rate limits."""
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=1024,
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                    ),
                )
                time.sleep(self._RATE_LIMIT_SLEEP)
                return (response.text or "").strip() or None
            except Exception as e:
                msg = str(e)
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    delay_match = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', msg)
                    wait = int(delay_match.group(1)) + 5 if delay_match else 30
                    print(f"  [!] Rate limited. Waiting {wait}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait)
                else:
                    print(f"  [!] Gemini API error: {e}")
                    return None
        print("  [!] Max retries exceeded — escalating.")
        return None

    def _parse_json_response(self, text: str) -> dict | None:
        """Safely parse JSON from LLM response."""
        if not text:
            return None
        try:
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except:
                    pass
        return None

    def _infer_company(self, issue: str, subject: str, company: str) -> str:
        """If company is None or ambiguous, use LLM to infer it."""
        if company and company.lower() not in ["none", "null", ""]:
            return company

        prompt = DOMAIN_CLASSIFIER_PROMPT.format(
            issue=issue,
            subject=subject or "",
            company=company or "None"
        )
        result = self._call_gemini(prompt)
        if result:
            for c in ["HackerRank", "Claude", "Visa"]:
                if c.lower() in result.lower():
                    return c
        return "Unknown"

    def _make_fallback_result(self, status: str, reason: str, risk_category: str = None) -> dict:
        """Generate a safe fallback result without LLM."""
        response = ESCALATION_RESPONSE if status == "escalated" else OUT_OF_SCOPE_RESPONSE
        return {
            "status": status,
            "product_area": risk_category or "general",
            "request_type": "product_issue",
            "response": response,
            "justification": reason
        }

    def process(self, issue: str, subject: str, company: str) -> dict:
        """
        Full triage pipeline for a single support ticket.
        Returns dict with: status, product_area, request_type, response, justification
        """

        # ── Step 1: Clean inputs ────────────────────────────────────────────
        issue = str(issue).strip() if issue else ""
        subject = str(subject).strip() if subject else ""
        company = str(company).strip() if company else ""

        if len(issue) < 5:
            return self._make_fallback_result(
                "escalated",
                "Issue text is too short or missing to process."
            )

        # ── Step 2: Infer company if needed ────────────────────────────────
        resolved_company = self._infer_company(issue, subject, company)

        # ── Step 3: Risk assessment (fast, rule-based) ─────────────────────
        risk = assess_risk(issue, resolved_company)
        if risk["should_escalate"]:
            return self._make_fallback_result(
                "escalated",
                risk["reason"],
                risk["risk_category"]
            )

        # ── Step 4: RAG retrieval ───────────────────────────────────────────
        query = f"{subject} {issue}".strip()
        docs = self.retriever.retrieve(
            query=query,
            company=resolved_company if resolved_company != "Unknown" else None,
            top_k=5
        )
        formatted_docs = self.retriever.format_docs_for_prompt(docs)

        # ── Step 5: LLM triage ─────────────────────────────────────────────
        prompt = TRIAGE_PROMPT.format(
            docs=formatted_docs,
            company=resolved_company,
            subject=subject or "(no subject)",
            issue=issue
        )

        raw_response = self._call_gemini(prompt)
        parsed = self._parse_json_response(raw_response)

        if not parsed:
            return self._make_fallback_result(
                "escalated",
                "LLM response could not be parsed — escalating for safety."
            )

        # ── Step 6: Validate and return ────────────────────────────────────
        valid_statuses = {"replied", "escalated"}
        valid_request_types = {"product_issue", "feature_request", "bug", "invalid"}

        status = parsed.get("status", "escalated")
        if status not in valid_statuses:
            status = "escalated"

        request_type = parsed.get("request_type", "product_issue")
        if request_type not in valid_request_types:
            request_type = "product_issue"

        return {
            "status": status,
            "product_area": parsed.get("product_area", resolved_company.lower()),
            "request_type": request_type,
            "response": parsed.get("response", ESCALATION_RESPONSE),
            "justification": parsed.get("justification", "See agent reasoning.")
        }
