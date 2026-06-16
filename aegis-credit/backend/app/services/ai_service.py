import json
import re
import anthropic
from app.config import settings

AI_MODEL = "claude-sonnet-4-6"

COMPLIANCE_DISCLAIMER = (
    "IMPORTANT: These are preliminary findings for investigator review only. "
    "No finding constitutes legal advice, a proven violation, or a guarantee of any outcome. "
    "All findings require human review before any action is taken."
)

TRADELINE_EXTRACTION_PROMPT = """You are a credit report analyst. Extract all tradelines (accounts) from this credit report text.

This text may be a single-bureau report, or a combined/tri-merge report containing data from multiple bureaus
(Experian, Equifax, TransUnion, Innovis) side by side or interleaved for the same accounts. If the same account
appears under more than one bureau, return ONE entry per bureau it appears under (do not merge them), since
each bureau's data for an account can differ.

Return a JSON array. Each object must have:
- bureau: string, one of "experian", "equifax", "transunion", "innovis" (your best identification of which
  bureau this specific entry's data came from; if the report is single-bureau and the bureau is unambiguous
  but not explicitly labeled per-account, use that report's bureau)
- creditor_name: string
- account_number_last4: string (last 4 digits only, or "????" if not available)
- account_type: string (e.g., "credit_card", "auto_loan", "mortgage", "student_loan", "collection", "other")
- open_date: string (YYYY-MM-DD format if available, else empty string)
- close_date: string (YYYY-MM-DD or empty)
- balance: number or null
- credit_limit: number or null
- payment_status: string (e.g., "current", "30_days_late", "60_days_late", "90_days_late", "charge_off", "collection", "paid", "closed")
- payment_history: string (summary of payment history)
- derogatory: boolean

Return ONLY the JSON array with no other text. If you genuinely find no account/tradeline data in the text,
return an empty array [] rather than guessing.

Credit report text:
"""

FINDINGS_PROMPT = """You are a credit investigator reviewing tradeline data for potential FCRA issues and discrepancies.

CRITICAL COMPLIANCE RULES:
- Never say "violation proven", "deletion guaranteed", or "legal advice"
- Every finding MUST be flagged as requiring human review
- Use language like "potential issue", "possible concern", "warrants investigation"

Analyze the tradelines and comparisons below. Return a JSON array of findings.

Each finding object must have:
- finding_type: "fcra_violation" | "discrepancy" | "derogatory" | "positive"
- severity: "high" | "medium" | "low" | "info"
- title: string (concise title)
- description: string (detailed description with specific data points)
- fcra_section: string (e.g., "FCRA §623", "FCRA §605", "FCRA §611" or empty if not applicable)
- requires_human_review: true (ALWAYS true)

Tradeline data:
{tradelines}

Cross-bureau comparisons:
{comparisons}

Return ONLY the JSON array with no other text.
"""

STRATEGY_PROMPT = """You are a credit restoration strategist. Based on the findings below, generate a prioritized action plan.

COMPLIANCE: All strategies are administrative recommendations. No strategy constitutes legal advice.
Label each item clearly as requiring client and investigator review before implementation.

Return a JSON array of strategy items. Each must have:
- priority: 1 (high), 2 (medium), or 3 (low)
- strategy_type: "dispute" | "goodwill" | "validation" | "pay_for_delete" | "consolidation" | "monitoring"
- title: string
- description: string
- action_items: array of strings
- estimated_timeline: string (e.g., "30-45 days", "60-90 days")

Findings:
{findings}

Client goal: {goal}

Return ONLY the JSON array with no other text.
"""


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _extract_json(content: str) -> str:
    """Pull a JSON array/object out of a Claude response, tolerating markdown code fences."""
    content = content.strip()
    match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def _parse_json_response(content: str) -> list[dict]:
    cleaned = _extract_json(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI returned malformed JSON ({e}). Raw response: {cleaned[:300]}") from e


def _require_api_key() -> None:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured in backend/.env.")


def extract_tradelines_from_text(raw_text: str) -> list[dict]:
    """Use Claude to extract structured tradeline data from raw credit report text."""
    _require_api_key()
    client = _client()
    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=8192,
            messages=[{"role": "user", "content": TRADELINE_EXTRACTION_PROMPT + raw_text[:60000]}],
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API call failed: {e}") from e
    return _parse_json_response(message.content[0].text)


def generate_findings(tradelines_data: list[dict], comparisons_data: list[dict]) -> list[dict]:
    """Use Claude to generate investigation findings from tradeline and comparison data."""
    _require_api_key()
    client = _client()
    prompt = FINDINGS_PROMPT.format(
        tradelines=json.dumps(tradelines_data, indent=2)[:8000],
        comparisons=json.dumps(comparisons_data, indent=2)[:4000],
    )
    try:
        message = client.messages.create(
            model=AI_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API call failed: {e}") from e
    findings = _parse_json_response(message.content[0].text)
    for f in findings:
        f["requires_human_review"] = True
    return findings


def generate_strategy(findings_data: list[dict], client_goal: str) -> list[dict]:
    """Use Claude to generate a credit restoration strategy."""
    _require_api_key()
    ai_client = _client()
    prompt = STRATEGY_PROMPT.format(
        findings=json.dumps(findings_data, indent=2)[:8000],
        goal=client_goal or "Improve credit score and remove inaccurate negative items",
    )
    try:
        message = ai_client.messages.create(
            model=AI_MODEL,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API call failed: {e}") from e
    return _parse_json_response(message.content[0].text)


def run_cross_bureau_comparison(tradelines_by_bureau: dict) -> list[dict]:
    """Compare tradelines across bureaus and identify discrepancies."""
    discrepancies = []
    bureaus = list(tradelines_by_bureau.keys())

    all_accounts: dict[str, dict] = {}
    for bureau, tradelines in tradelines_by_bureau.items():
        for tl in tradelines:
            key = (tl.get("creditor_name", "").lower(), tl.get("account_number_last4", ""))
            if key not in all_accounts:
                all_accounts[key] = {}
            all_accounts[key][bureau] = tl

    for (creditor, last4), bureau_data in all_accounts.items():
        present_bureaus = list(bureau_data.keys())
        all_bureaus_in_set = list(tradelines_by_bureau.keys())

        missing = [b for b in all_bureaus_in_set if b not in present_bureaus]
        if missing and len(present_bureaus) >= 2:
            discrepancies.append({
                "creditor_name": creditor,
                "account_number_last4": last4,
                "discrepancy_type": "missing",
                "bureaus_affected": missing,
                "details": f"Account appears on {present_bureaus} but NOT on {missing}",
                "severity": "medium",
            })

        if len(present_bureaus) >= 2:
            statuses = {b: bureau_data[b].get("payment_status", "") for b in present_bureaus}
            unique_statuses = set(statuses.values())
            if len(unique_statuses) > 1:
                discrepancies.append({
                    "creditor_name": creditor,
                    "account_number_last4": last4,
                    "discrepancy_type": "status",
                    "bureaus_affected": present_bureaus,
                    "details": f"Payment status differs across bureaus: {statuses}",
                    "severity": "high",
                })

            balances = {b: bureau_data[b].get("balance") for b in present_bureaus if bureau_data[b].get("balance") is not None}
            if len(balances) >= 2:
                vals = list(balances.values())
                if max(vals) - min(vals) > 50:
                    discrepancies.append({
                        "creditor_name": creditor,
                        "account_number_last4": last4,
                        "discrepancy_type": "balance",
                        "bureaus_affected": list(balances.keys()),
                        "details": f"Balance discrepancy across bureaus: {balances}",
                        "severity": "medium",
                    })

    return discrepancies
