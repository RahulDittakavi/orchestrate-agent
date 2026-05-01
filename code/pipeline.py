"""
pipeline.py — Core triage pipeline. Orchestrates all components.
"""

import json
import re
import google.generativeai as genai
from prompts import TRIAGE_PROMPT, DOMAIN_CLASSIFIER_PROMPT
from retriever import Retriever
from risk import assess_risk

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
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel("gemini-1.5-pro")
        self.retriever = Retriever()
        print("[✓] Pipeline initialized")

    def _call_gemini(self, prompt: str) -> str:
        """Call Gemini with retry on failure."""
        try:
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,          # Low temp = consistent, factual output
                    max_output_tokens=1024,
                )
            )
            return response.text.strip()
        except Exception as e:
            print(f"  [!] Gemini API error: {e}")
            return None

    def _parse_json_response(self, text: str) -> dict | None:
        """Safely parse JSON from LLM response."""
        if not text:
            return None
        try:
            # Strip markdown code fences if present
            clean = re.sub(r"```json|```", "", text).strip()
            return json.loads(clean)
        except json.JSONDecodeError:
            # Try to extract JSON block from response
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
            result = result.strip()
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

        # Handle empty/garbage input
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
            # LLM failed — safe fallback
            return self._make_fallback_result(
                "escalated",
                "LLM response could not be parsed — escalating for safety."
            )

        # ── Step 6: Validate and return ────────────────────────────────────
        return {
            "status": parsed.get("status", "escalated"),
            "product_area": parsed.get("product_area", resolved_company.lower()),
            "request_type": parsed.get("request_type", "product_issue"),
            "response": parsed.get("response", ESCALATION_RESPONSE),
            "justification": parsed.get("justification", "See agent reasoning.")
        }
