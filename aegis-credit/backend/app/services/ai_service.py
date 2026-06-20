import json
import re
import time
import anthropic
from app.config import settings

AI_MODEL = "claude-sonnet-4-6"

COMPLIANCE_DISCLAIMER = (
    "IMPORTANT: These are preliminary findings for investigator review only. "
    "No finding constitutes legal advice, a proven violation, or a guarantee of any outcome. "
    "All findings require human review before any action is taken."
)

TRADELINE_EXTRACTION_PROMPT = """You are a credit report analyst. Extract EVERY tradeline (account) from this credit report text —
not just the first section. Consumer credit reports typically list accounts in several separate sections such as
"Credit cards", "Loans", "Closed accounts", "Collections", "Charge-offs", or "Negative accounts" — you MUST scan
the entire document end-to-end and extract accounts from ALL of these sections, not only the first/positive one.

This text may be a single-bureau report, or a combined/tri-merge report containing data from multiple bureaus
(Experian, Equifax, TransUnion, Innovis) side by side or interleaved for the same accounts. If the same account
appears under more than one bureau, return ONE entry per bureau it appears under (do not merge them), since
each bureau's data for an account can differ.

Tri-merge reports commonly print one account block per creditor with THREE columns of values (e.g.
"Transunion® Experian® Equifax®") side by side for fields like Account #, Balance Owed, Account Status,
Payment Status, etc. A column filled with "--" for every field for that account means that bureau does NOT
report this account at all — do not create a tradeline entry for that bureau/account combination. Only emit
an entry for a bureau column that has actual data (account number, balance, dates, or status other than "--").
For example, if a block shows Account # as "-- -- 300002***" across Transunion/Experian/Equifax, only Equifax
has this account — emit exactly one tradeline (bureau=equifax), not three.

The report usually contains an "Account summary" section near the top with per-bureau counts like "Open accounts",
"Closed accounts", "Delinquent", "Derogatory", and "Collections". Use these counts as a completeness check — your
extracted tradelines should account for all of them. If a bureau's summary says e.g. 4 derogatory and 2 collections
accounts, make sure your output includes tradelines reflecting that, not just the clean/current ones.

To determine payment_status and derogatory for each account, look for report fields such as "Account Status"
(Open/Closed), "Current Payment Status", "Current Rating", "Highest Adverse Rating", "Most Recent Adverse", and
"Times 30/60/90 Days Late". Do NOT default to "current" — only use "current" when the report explicitly indicates
the account is open and in good standing with no adverse rating. If any field mentions collection, charge-off,
late payment, repossession, foreclosure, or bankruptcy for an account, set derogatory=true and choose the most
specific matching payment_status.

Return a JSON array. Each object must have:
- bureau: string, one of "experian", "equifax", "transunion", "innovis" (your best identification of which
  bureau this specific entry's data came from; if the report is single-bureau and the bureau is unambiguous
  but not explicitly labeled per-account, use that report's bureau)
- creditor_name: string
- account_number_last4: string (last 4 visible digits of the account number. Some reports mask the END of the
  account number with asterisks and only show the START unmasked, e.g. "300002***********" — in that case use
  the visible leading digits instead, since there is no true "last 4" to extract. Use "????" only if no digits
  are visible at all)
- account_type: string (e.g., "credit_card", "auto_loan", "mortgage", "student_loan", "collection", "other")
- open_date: string (YYYY-MM-DD format if available, else empty string)
- close_date: string (YYYY-MM-DD or empty)
- balance: number or null
- credit_limit: number or null
- payment_status: string (e.g., "current", "30_days_late", "60_days_late", "90_days_late", "charge_off", "collection", "paid", "closed")
- payment_history: string (ONE short sentence summary, under 100 characters — do not transcribe month-by-month grids)
- derogatory: boolean (true if the account shows any adverse/negative status — collection, charge-off, late
  payment, repossession, foreclosure, bankruptcy, or closed-for-default)
- high_balance: number or null (highest balance this account has ever reached, labeled "High Balance" or "High Credit")
- past_due_amount: number or null
- scheduled_payment_amount: number or null (regular monthly payment amount)
- payment_rating: string (Metro 2 payment rating if visible: "0"=too new, "1"=current, "2"=30 days, "3"=60 days, "4"=90 days, "5"=120 days, "6"=150 days, "7"=collection, "8"=charge-off, "9"=repo; leave empty string if not shown)
- compliance_condition_code: string (XF, XH, XJ, XR, XO or X1-X9 if visible; empty string otherwise)
- consumer_information_indicator: string (bankruptcy indicator code if visible A-J; empty string otherwise)
- dofd: string (Date of First Delinquency in YYYY-MM-DD format if shown; empty string otherwise — this is the date the account first became delinquent and was never brought current, distinct from open_date or close_date)
- date_reported: string (YYYY-MM-DD — the date this bureau last updated the account in their records)
- remarks: string (any creditor remarks or special comments verbatim, empty string if none)

Return ONLY the JSON array with no other text. If you genuinely find no account/tradeline data anywhere in the
text, return an empty array [] rather than guessing — but do not stop after the first section if more accounts
follow later in the document.

Credit report text:
"""

FINDINGS_PROMPT = """You are a credit investigator reviewing tradeline data for potential FCRA/FDCPA issues and discrepancies.

CRITICAL COMPLIANCE RULES:
- Never say "violation proven", "deletion guaranteed", or "legal advice"
- Every finding MUST be flagged as requiring human review
- Use language like "potential issue", "possible concern", "warrants investigation"

KEY LAWS TO REFERENCE (use the most specific section that applies):
FCRA: §604 (permissible purpose), §605(a) (7-yr obsolescence/10-yr bankruptcy), §605B (ID theft block),
      §609 (consumer disclosure rights), §611 (CRA 30-day reinvestigation duty),
      §612 (free annual report rights), §613 (public record reporting),
      §615 (adverse action notice to consumer), §616 (willful noncompliance — $100-$1,000 statutory damages),
      §617 (negligent noncompliance — actual damages), §619 (false pretenses — criminal),
      §623 (furnisher accuracy / dispute investigation duty)
FDCPA: §1692c (communication restrictions — time/place/employer/attorney),
       §1692d (harassment/abuse prohibition), §1692e (false/misleading representations),
       §1692f (unfair collection means), §1692g (30-day debt validation notice),
       §1692k (civil liability — $1,000 statutory damages per action)
OTHER: FACTA §315 (fraud alerts, ID theft blocks), ECOA §1691 (credit discrimination),
       SCRA §3901 (servicemember 6% interest cap / stay of proceedings)

Analyze the tradelines and comparisons below. Return a JSON array of findings.

Each finding object must have:
- finding_type: "fcra_violation" | "fdcpa_violation" | "discrepancy" | "derogatory" | "positive"
- severity: "high" | "medium" | "low" | "info"
- title: string (concise title)
- description: string (detailed description with specific data points)
- fcra_section: string (most specific applicable section, e.g., "FCRA §623(b)", "FDCPA §1692g", or empty)
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

Return a JSON array of UP TO 5 strategy items (the most important ones only). Keep descriptions under 100 words each. Each must have:
- priority: 1 (high), 2 (medium), or 3 (low)
- strategy_type: "dispute" | "goodwill" | "validation" | "pay_for_delete" | "consolidation" | "monitoring"
- title: string (concise, under 10 words)
- description: string (under 100 words)
- action_items: array of 2-3 short strings
- estimated_timeline: string (e.g., "30-45 days")

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
    # Try full fence first: ```json ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if match:
        return match.group(1).strip()
    # Opening fence only (truncated response): ```json ...
    match = re.search(r"```(?:json)?\s*([\s\S]+)", content)
    if match:
        return match.group(1).strip()
    return content


def _parse_json_response(content: str) -> list[dict]:
    cleaned = _extract_json(content)
    # Try as-is first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Find where the JSON array/object starts
    for ch in ['[', '{']:
        idx = cleaned.find(ch)
        if idx < 0:
            continue
        fragment = cleaned[idx:]
        # Try as-is
        try:
            result = json.loads(fragment)
            return result if isinstance(result, list) else [result]
        except json.JSONDecodeError:
            pass
        # Try to repair truncated JSON: find last complete object and close the array
        last_brace = fragment.rfind('}')
        if last_brace >= 0:
            repaired = fragment[:last_brace + 1] + ']'
            try:
                result = json.loads(repaired)
                return result if isinstance(result, list) else [result]
            except json.JSONDecodeError:
                pass
    raise RuntimeError(f"AI returned malformed JSON. Raw response: {content[:300]}")


def _require_api_key() -> None:
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured in backend/.env.")


def _retry_after_seconds(e: anthropic.APIStatusError, default: float) -> float:
    try:
        header = e.response.headers.get("retry-after")
        return float(header) if header else default
    except Exception:
        return default


def _create_message(client: anthropic.Anthropic, **kwargs):
    """Call the Anthropic API with retries for transient server-side errors and rate limits."""
    last_error: Exception | None = None
    attempts = 4
    for attempt in range(attempts):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            last_error = e
            if attempt < attempts - 1:
                time.sleep(_retry_after_seconds(e, default=15 * (attempt + 1)))
                continue
            raise RuntimeError(
                f"Anthropic API rate limit hit and retries exhausted: {e}. "
                "If you just added billing/credits, your account may still be on a low usage tier — "
                "wait a minute and try Reparse again."
            ) from e
        except (anthropic.InternalServerError, anthropic.APIConnectionError) as e:
            last_error = e
            if attempt < attempts - 1:
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(f"Anthropic API call failed after retries: {e}") from e
        except anthropic.APIError as e:
            raise RuntimeError(f"Anthropic API call failed: {e}") from e
    raise RuntimeError(f"Anthropic API call failed after retries: {last_error}")


def extract_tradelines_from_text(raw_text: str) -> list[dict]:
    """Use Claude to extract structured tradeline data from raw credit report text."""
    _require_api_key()
    client = _client()
    message = _create_message(
        client,
        model=AI_MODEL,
        max_tokens=16000,
        messages=[{"role": "user", "content": TRADELINE_EXTRACTION_PROMPT + raw_text[:60000]}],
    )
    return _parse_json_response(message.content[0].text)


def generate_findings(tradelines_data: list[dict], comparisons_data: list[dict]) -> list[dict]:
    """Use Claude to generate investigation findings from tradeline and comparison data."""
    _require_api_key()
    client = _client()
    prompt = FINDINGS_PROMPT.format(
        tradelines=json.dumps(tradelines_data, indent=2)[:8000],
        comparisons=json.dumps(comparisons_data, indent=2)[:4000],
    )
    message = _create_message(
        client,
        model=AI_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
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
    message = _create_message(
        ai_client,
        model=AI_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
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


REPORT_EXTRACTION_PROMPT = """You are a credit report analyst. Extract ALL tradelines, inquiries, and personal information from this credit report text.

TRADELINES:
Extract every tradeline (account) from this report — including accounts from all sections such as
"Credit cards", "Loans", "Closed accounts", "Collections", "Charge-offs", and "Negative accounts".
For tri-merge reports, create one entry per bureau that actually reports the account (skip bureaus showing "--").

INQUIRIES:
Extract all inquiries from sections labeled "Inquiries", "Credit Checks", or "Requests for your credit history".
For each inquiry provide:
- bureau: which bureau recorded this inquiry
- inquiry_type: "hard" or "soft" (hard = credit check by a lender; soft = promotional, employment, monitoring)
- subscriber_name: name of the company that pulled the credit
- inquiry_date: YYYY-MM-DD format if available, else empty string
- purpose: purpose stated in the report, or empty string if not shown

PERSONAL INFORMATION:
Extract the personal information section for each bureau present. For each bureau provide:
- bureau: bureau name (experian, equifax, transunion, innovis)
- current_name: consumer's current name as listed
- aliases: array of other names/aliases listed
- current_address: most recent address
- previous_addresses: array of previous addresses
- current_employer: most recent employer listed
- previous_employers: array of previous employers
- phone_numbers: array of phone numbers listed
- dob: date of birth in YYYY-MM-DD format if shown, else empty string
- ssn_last4: last 4 digits of SSN if shown, else empty string

Return a JSON OBJECT (not an array) with exactly three keys:
{
  "tradelines": [ ... array of tradeline objects ... ],
  "inquiries": [ ... array of inquiry objects ... ],
  "personal_info": [ ... array of per-bureau PI objects ... ]
}

Tradeline object fields (same as always):
bureau, creditor_name, account_number_last4, account_type, open_date, close_date,
balance, credit_limit, payment_status, payment_history, derogatory, high_balance,
past_due_amount, scheduled_payment_amount, payment_rating, compliance_condition_code,
consumer_information_indicator, dofd, date_reported, remarks

Return ONLY the JSON object with no other text.

Credit report text:
"""


def _parse_json_object_response(content: str) -> dict:
    """Parse a JSON object response from Claude."""
    cleaned = _extract_json(content)
    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        # If AI returned an array instead of an object, wrap it
        if isinstance(result, list):
            return {"tradelines": result, "inquiries": [], "personal_info": []}
        raise RuntimeError("AI returned unexpected JSON type")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"AI returned malformed JSON ({e}). Raw response: {cleaned[:300]}") from e


def extract_report_data(raw_text: str) -> dict:
    """
    Use Claude to extract tradelines, inquiries, and personal info from credit report text.

    Returns:
        {
            "tradelines": [...],
            "inquiries": [...],
            "personal_info": [...]
        }
    """
    _require_api_key()
    client = _client()
    message = _create_message(
        client,
        model=AI_MODEL,
        max_tokens=8192,
        messages=[{"role": "user", "content": REPORT_EXTRACTION_PROMPT + raw_text[:60000]}],
    )
    result = _parse_json_object_response(message.content[0].text)
    # Ensure all expected keys are present
    result.setdefault("tradelines", [])
    result.setdefault("inquiries", [])
    result.setdefault("personal_info", [])
    return result
