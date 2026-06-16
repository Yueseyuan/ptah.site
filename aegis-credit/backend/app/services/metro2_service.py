"""Metro 2 rules engine — pure Python, no external deps beyond stdlib."""
from datetime import date, datetime
from typing import Optional


def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _today() -> date:
    return date.today()


# ---------------------------------------------------------------------------
# Individual rule functions — each returns a list of finding dicts (0 or 1).
# ---------------------------------------------------------------------------

def _rule_dofd_7yr(tl) -> list:
    """DOFD_7YR: derogatory account whose DOFD is more than 7 years ago."""
    if not tl.derogatory:
        return []
    dofd = _parse_date(tl.dofd)
    if dofd is None:
        return []
    delta = (_today() - dofd).days
    if delta > 7 * 365:
        years = delta / 365
        return [{
            "tradeline_id": tl.id,
            "rule_code": "DOFD_7YR",
            "rule_name": "Derogatory Account Exceeds 7-Year Reporting Window",
            "severity": "high",
            "description": (
                f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) has a Date of First Delinquency "
                f"of {tl.dofd}, which is approximately {years:.1f} years ago. "
                "Under FCRA §605(a), most derogatory items must be removed from credit reports "
                "no later than 7 years from the DOFD. This account may warrant a deletion dispute."
            ),
            "fcra_section": "FCRA §605(a)",
        }]
    return []


def _rule_missing_dofd(tl) -> list:
    """MISSING_DOFD: derogatory account with no DOFD."""
    if not tl.derogatory:
        return []
    if tl.dofd and tl.dofd.strip():
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "MISSING_DOFD",
        "rule_name": "Missing Date of First Delinquency on Negative Account",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) is marked derogatory but "
            "has no Date of First Delinquency (DOFD) recorded. "
            "The Metro 2 Credit Reporting Resource Guide requires furnishers to report DOFD on "
            "all accounts with derogatory payment history. Missing DOFD makes it impossible to "
            "verify the 7-year reporting clock under FCRA §605(a)."
        ),
        "fcra_section": "FCRA §605(a)",
    }]


def _rule_balance_exceeds_high(tl) -> list:
    """BALANCE_EXCEEDS_HIGH: current balance greater than historical high balance."""
    if tl.balance is None or tl.high_balance is None:
        return []
    if tl.balance > tl.high_balance + 1:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "BALANCE_EXCEEDS_HIGH",
            "rule_name": "Current Balance Exceeds High Balance",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) reports a current balance "
                f"of ${tl.balance:,.2f}, which exceeds the reported high balance of "
                f"${tl.high_balance:,.2f}. Per Metro 2 spec, the high balance field must reflect "
                "the highest balance ever reached; a current balance above it indicates a data "
                "inconsistency that may need furnisher correction."
            ),
            "fcra_section": "",
        }]
    return []


def _rule_past_due_on_current(tl) -> list:
    """PAST_DUE_ON_CURRENT: account reported current but shows a past-due amount."""
    if (tl.payment_status or "").lower() != "current":
        return []
    if tl.past_due_amount is None or tl.past_due_amount <= 0:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "PAST_DUE_ON_CURRENT",
        "rule_name": "Past Due Amount Reported on a Current Account",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) has payment status 'current' "
            f"but also reports a past-due amount of ${tl.past_due_amount:,.2f}. "
            "These two fields are mutually inconsistent. Under Metro 2 spec, a current account "
            "should have a past-due amount of $0. This inconsistency may constitute inaccurate "
            "reporting under FCRA §623."
        ),
        "fcra_section": "FCRA §623",
    }]


def _rule_zero_past_due_on_derogatory(tl) -> list:
    """ZERO_PAST_DUE_ON_DEROGATORY: derogatory account shows $0 past-due when it shouldn't."""
    if not tl.derogatory:
        return []
    if tl.past_due_amount is None:
        return []
    if tl.past_due_amount != 0:
        return []
    closed_statuses = {"paid", "closed", "charge_off"}
    status = (tl.payment_status or "").lower()
    if status in closed_statuses:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "ZERO_PAST_DUE_ON_DEROGATORY",
        "rule_name": "Derogatory Account Shows Zero Past-Due Amount",
        "severity": "low",
        "description": (
            f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) is marked derogatory with "
            f"payment status '{tl.payment_status}' but reports a past-due amount of $0. "
            "For open derogatory accounts that are not paid/closed/charged-off, the past-due "
            "amount is typically expected to be non-zero. This may indicate an unreported past-due "
            "balance or a data entry error by the furnisher."
        ),
        "fcra_section": "",
    }]


def _rule_stale_reporting(tl) -> list:
    """STALE_REPORTING: date_reported is more than 730 days ago."""
    dr = _parse_date(tl.date_reported)
    if dr is None:
        return []
    delta = (_today() - dr).days
    if delta > 730:
        years = delta / 365
        return [{
            "tradeline_id": tl.id,
            "rule_code": "STALE_REPORTING",
            "rule_name": "Stale Account Reporting (No Update in 2+ Years)",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' (bureau: {tl.bureau}) was last reported on "
                f"{tl.date_reported}, approximately {years:.1f} years ago. "
                "Furnishers are expected to update account information regularly. Stale data "
                "may be inaccurate and should be verified or updated per FCRA §623."
            ),
            "fcra_section": "FCRA §623",
        }]
    return []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_RULES = [
    _rule_dofd_7yr,
    _rule_missing_dofd,
    _rule_balance_exceeds_high,
    _rule_past_due_on_current,
    _rule_zero_past_due_on_derogatory,
    _rule_stale_reporting,
]


def run_metro2_rules(tradelines: list) -> list[dict]:
    """Run all Metro 2 rules against a list of Tradeline ORM objects.

    Returns a list of finding dicts with keys:
        tradeline_id, rule_code, rule_name, severity, description, fcra_section
    """
    findings: list[dict] = []
    for tl in tradelines:
        for rule_fn in _RULES:
            try:
                findings.extend(rule_fn(tl))
            except Exception:
                # Defensive: never let a single rule crash the whole analysis
                pass
    return findings
