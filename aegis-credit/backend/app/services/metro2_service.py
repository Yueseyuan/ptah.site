"""
Metro 2 Credit Reporting Resource Guide (CRRG) compliance engine.
Based on the CDIA Metro 2 Format specification and FCRA/FDCPA regulatory framework.
Covers: FCRA §§604-625, FDCPA §§1692a-k, 11 U.S.C. §524, Metro 2 CRRG §§1-4.
All findings require human review — this tool identifies potential issues only.
"""
from datetime import date, datetime
from typing import Optional


# ── Metro 2 Reference Tables ──────────────────────────────────────────────────

VALID_PAYMENT_RATINGS = set("0123456789BDEGHJ")

VALID_COMPLIANCE_CONDITION_CODES = {
    "XF", "XH", "XJ", "XR", "XO",
    "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9",
    "XA", "XB", "XC", "XD", "XE",
}

VALID_CONSUMER_INFO_INDICATORS = set("ABCDEFGHIJK")

PAYMENT_RATING_LABELS = {
    "0": "Too new to rate / approved not used",
    "1": "Pays as agreed / current",
    "2": "30–59 days past due",
    "3": "60–89 days past due",
    "4": "90–119 days past due",
    "5": "120–149 days past due",
    "6": "150–179 days past due",
    "7": "In collection / skip",
    "8": "Charge-off",
    "9": "Repossession / foreclosure / partial plan",
    "B": "No payment history available",
    "D": "30–59 DPD (alternate)",
    "E": "60–89 DPD (alternate)",
    "G": "Collection (alternate)",
    "H": "Foreclosure (alternate)",
    "J": "Voluntary surrender (alternate)",
}

CONSUMER_INFO_INDICATOR_LABELS = {
    "A": "Chapter 7 bankruptcy — petition filed",
    "B": "Chapter 11 bankruptcy — petition filed",
    "C": "Chapter 12 bankruptcy — petition filed",
    "D": "Chapter 13 bankruptcy — petition filed",
    "E": "Chapter 7 — voluntary surrender",
    "F": "Chapter 11 — voluntary surrender",
    "G": "Chapter 12 — voluntary surrender",
    "H": "Chapter 13 — voluntary surrender",
    "I": "Chapter 7 — discharged",
    "J": "Chapter 13 — discharged",
    "K": "Chapter 7 — discharged and reaffirmed",
}

COMPLIANCE_CONDITION_LABELS = {
    "XF": "Account information in dispute under FCRA §611",
    "XH": "Account information in dispute under Fair Credit Billing Act (open-end)",
    "XJ": "Account closed due to transfer",
    "XR": "Removal of prior-reported information",
    "XO": "Account sold / transferred to another company",
    "X1": "Account closed by consumer",
    "X2": "Account closed by grantor",
    "X3": "Account purchased by another lender",
    "X4": "Account acquired through merger/acquisition",
    "X5": "Account in foreclosure",
    "X6": "Account transferred due to merger",
    "X7": "Consumer location unknown",
    "X8": "Account in active litigation",
    "X9": "Account belongs to deceased consumer",
}

# Payment status → expected Metro 2 payment rating
STATUS_TO_RATING = {
    "current":      "1",
    "30_days_late": "2",
    "60_days_late": "3",
    "90_days_late": "4",
    "charge_off":   "8",
    "collection":   "7",
    "repossession": "9",
    "foreclosure":  "9",
    "paid":         "1",
    "closed":       "1",
}

# Statuses that require a DOFD
REQUIRES_DOFD = {
    "30_days_late", "60_days_late", "90_days_late",
    "charge_off", "collection", "repossession", "foreclosure",
}

# Bankruptcy indicators where balance should be $0 (discharged)
DISCHARGED_INDICATORS = {"I", "J", "K"}

# All bankruptcy indicators
BANKRUPTCY_INDICATORS = set("ABCDEFGHIJK")


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _rating_label(r: str) -> str:
    return PAYMENT_RATING_LABELS.get(r.upper(), "unknown")


# ── Individual tradeline rules ────────────────────────────────────────────────
# Each function takes a single ORM Tradeline object and returns a list of finding dicts.

def _rule_dofd_7yr(tl) -> list:
    """DOFD_7YR — FCRA §605(a): 7-year reporting window exceeded."""
    if not tl.derogatory:
        return []
    dofd = _parse_date(tl.dofd)
    if dofd is None:
        return []
    delta = (_today() - dofd).days
    if delta > 7 * 365:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "DOFD_7YR",
            "rule_name": "Derogatory Account Exceeds 7-Year Reporting Window",
            "severity": "high",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) DOFD {tl.dofd} is "
                f"{delta/365:.1f} years ago. FCRA §605(a) limits most adverse reporting "
                f"to 7 years from DOFD. This account is potentially obsolete and warrants "
                f"an immediate deletion dispute under FCRA §611."
            ),
            "fcra_section": "FCRA §605(a); Metro 2 CRRG §1.2",
        }]
    return []


def _rule_dofd_approaching(tl) -> list:
    """DOFD_APPROACHING — account within 6 months of 7-year FCRA §605(a) cutoff."""
    if not tl.derogatory:
        return []
    dofd = _parse_date(tl.dofd)
    if dofd is None:
        return []
    cutoff = date(dofd.year + 7, dofd.month, dofd.day)
    days_left = (cutoff - _today()).days
    if 0 < days_left <= 180:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "DOFD_APPROACHING",
            "rule_name": "Account Approaching 7-Year FCRA Reporting Limit",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) DOFD {tl.dofd} — "
                f"the 7-year FCRA §605(a) window expires in {days_left} day(s) ({cutoff}). "
                f"Verify that automated suppression is scheduled on time."
            ),
            "fcra_section": "FCRA §605(a)",
        }]
    return []


def _rule_missing_dofd(tl) -> list:
    """MISSING_DOFD — Metro 2 CRRG §1.5: derogatory account with no DOFD populated."""
    if not tl.derogatory:
        return []
    status = (tl.payment_status or "").lower()
    if status not in REQUIRES_DOFD:
        return []
    if tl.dofd and tl.dofd.strip():
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "MISSING_DOFD",
        "rule_name": "Missing Date of First Delinquency on Derogatory Account",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is derogatory "
            f"(payment_status='{tl.payment_status}') with no DOFD. Metro 2 CRRG §1.5 "
            f"requires DOFD on all derogatory accounts. Without it, the FCRA §605(a) "
            f"7-year reporting clock cannot be verified or challenged."
        ),
        "fcra_section": "FCRA §605(a); Metro 2 CRRG §1.5",
    }]


def _rule_dofd_future(tl) -> list:
    """DOFD_FUTURE — DOFD is in the future: impossible, likely re-aging."""
    dofd = _parse_date(tl.dofd)
    if dofd is None or dofd <= _today():
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DOFD_FUTURE",
        "rule_name": "Date of First Delinquency Is in the Future (Re-Aging Indicator)",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) DOFD {tl.dofd} is a future date — "
            f"impossible, as delinquency cannot begin in the future. This is a strong "
            f"indicator of re-aging — the illegal practice of resetting DOFD to extend the "
            f"7-year FCRA §605(a) reporting window."
        ),
        "fcra_section": "FCRA §605(a); FCRA §623(a)(1); Metro 2 CRRG §1.5",
    }]


def _rule_dofd_after_reported(tl) -> list:
    """DOFD_AFTER_REPORTED — DOFD after Date Reported: impossible date sequence, re-aging."""
    dofd = _parse_date(tl.dofd)
    dr = _parse_date(tl.date_reported)
    if dofd is None or dr is None or dofd <= dr:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DOFD_AFTER_REPORTED",
        "rule_name": "DOFD Is After Date Reported — Impossible Sequence (Re-Aging)",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) DOFD {tl.dofd} is AFTER "
            f"Date Reported {tl.date_reported}. Delinquency must precede reporting. "
            f"This strongly indicates re-aging — a violation of FCRA §605(a)."
        ),
        "fcra_section": "FCRA §605(a); FCRA §623(a)(1); Metro 2 CRRG §1.5",
    }]


def _rule_dofd_before_open(tl) -> list:
    """DOFD_BEFORE_OPEN — DOFD predates account open date: impossible sequence."""
    dofd = _parse_date(tl.dofd)
    opened = _parse_date(tl.open_date)
    if dofd is None or opened is None or dofd >= opened:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DOFD_BEFORE_OPEN",
        "rule_name": "DOFD Predates Account Open Date — Data Integrity Error",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) has DOFD {tl.dofd} which is "
            f"before account open date {tl.open_date}. An account cannot become delinquent "
            f"before it was opened. This is a data integrity error that may indicate "
            f"incorrect DOFD (possible re-aging) or mis-assigned account data."
        ),
        "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §1.5",
    }]


def _rule_balance_exceeds_high(tl) -> list:
    """BALANCE_EXCEEDS_HIGH — current balance greater than historical high balance."""
    if tl.balance is None or tl.high_balance is None:
        return []
    if float(tl.balance) > float(tl.high_balance) + 1:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "BALANCE_EXCEEDS_HIGH",
            "rule_name": "Current Balance Exceeds Historical High Balance",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) current balance "
                f"${float(tl.balance):,.2f} exceeds high balance ${float(tl.high_balance):,.2f}. "
                f"Metro 2 CRRG §2.3 requires high_balance to reflect the highest ever balance. "
                f"A current balance above it indicates post-charge-off fee accrual or a "
                f"furnisher data error under FCRA §623(a)(1)."
            ),
            "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.3",
        }]
    return []


def _rule_past_due_on_current(tl) -> list:
    """PAST_DUE_ON_CURRENT — current account with a positive past-due amount."""
    if (tl.payment_status or "").lower() != "current":
        return []
    if tl.past_due_amount is None or float(tl.past_due_amount) <= 0:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "PAST_DUE_ON_CURRENT",
        "rule_name": "Past-Due Amount on Account Marked Current",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is 'current' but reports "
            f"past_due_amount=${float(tl.past_due_amount):,.2f}. These fields are mutually "
            f"exclusive: a current account must have $0 past-due per Metro 2 CRRG §2.4. "
            f"This inconsistency is inaccurate reporting under FCRA §623."
        ),
        "fcra_section": "FCRA §623; Metro 2 CRRG §2.4",
    }]


def _rule_zero_past_due_on_derogatory(tl) -> list:
    """ZERO_PAST_DUE_ON_DEROGATORY — open derogatory account with $0 past-due."""
    if not tl.derogatory:
        return []
    if tl.past_due_amount is None or tl.past_due_amount != 0:
        return []
    status = (tl.payment_status or "").lower()
    if status in {"paid", "closed", "charge_off"}:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "ZERO_PAST_DUE_ON_DEROGATORY",
        "rule_name": "Open Derogatory Account Shows Zero Past-Due Amount",
        "severity": "low",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is derogatory "
            f"('{tl.payment_status}') but past_due_amount=$0. Active derogatory accounts "
            f"should reflect a non-zero past-due balance per Metro 2 CRRG §2.4."
        ),
        "fcra_section": "Metro 2 CRRG §2.4",
    }]


def _rule_stale_reporting(tl) -> list:
    """STALE_REPORTING — no update in 2+ years, violating Metro 2 monthly update requirement."""
    dr = _parse_date(tl.date_reported)
    if dr is None:
        return []
    delta = (_today() - dr).days
    if delta > 730:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "STALE_REPORTING",
            "rule_name": "Stale Account Reporting — No Update in 2+ Years",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) was last reported {tl.date_reported} "
                f"({delta/365:.1f} years ago). Metro 2 CRRG §1.4 requires monthly furnisher "
                f"updates. Stale data may be inaccurate and violate FCRA §623(a)(1) accuracy "
                f"requirements."
            ),
            "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §1.4",
        }]
    return []


def _rule_payment_rating_mismatch(tl) -> list:
    """PAYMENT_RATING_MISMATCH — payment_rating code inconsistent with payment_status."""
    status = (tl.payment_status or "").lower()
    rating = (tl.payment_rating or "").strip()
    if not status or not rating:
        return []
    expected = STATUS_TO_RATING.get(status)
    if expected and rating not in (expected, "0", "B", ""):
        return [{
            "tradeline_id": tl.id,
            "rule_code": "PAYMENT_RATING_MISMATCH",
            "rule_name": "Metro 2 Payment Rating Inconsistent with Payment Status",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) payment_status='{status}' "
                f"(expected rating '{expected}') but payment_rating='{rating}' "
                f"({_rating_label(rating)}). Metro 2 CRRG §2.1 requires these to be consistent."
            ),
            "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.1",
        }]
    return []


def _rule_invalid_payment_rating(tl) -> list:
    """INVALID_PAYMENT_RATING — unrecognized Metro 2 payment rating code."""
    rating = (tl.payment_rating or "").strip()
    if not rating or rating.upper() in VALID_PAYMENT_RATINGS:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "INVALID_PAYMENT_RATING",
        "rule_name": "Unrecognized Metro 2 Payment Rating Code",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) has payment_rating='{rating}', "
            f"which is not a valid Metro 2 code. Valid codes: 0–9, B, D, E, G, H, J."
        ),
        "fcra_section": "Metro 2 CRRG §2.1",
    }]


def _rule_invalid_compliance_code(tl) -> list:
    """INVALID_COMPLIANCE_CODE — unrecognized Metro 2 Compliance Condition Code."""
    code = (tl.compliance_condition_code or "").strip().upper()
    if not code or code in VALID_COMPLIANCE_CONDITION_CODES:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "INVALID_COMPLIANCE_CODE",
        "rule_name": "Unrecognized Metro 2 Compliance Condition Code",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) has compliance_condition_code='{code}', "
            f"which is not a recognized Metro 2 code. Valid codes: XF, XH, XJ, XR, XO, X1–X9."
        ),
        "fcra_section": "Metro 2 CRRG §2.7",
    }]


def _rule_invalid_consumer_info(tl) -> list:
    """INVALID_CONSUMER_INFO — unrecognized Metro 2 Consumer Information Indicator."""
    code = (tl.consumer_information_indicator or "").strip().upper()
    if not code or code in VALID_CONSUMER_INFO_INDICATORS:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "INVALID_CONSUMER_INFO",
        "rule_name": "Unrecognized Metro 2 Consumer Information Indicator",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) consumer_information_indicator='{code}' "
            f"is not a valid Metro 2 code. Valid codes are A–K (bankruptcy indicators)."
        ),
        "fcra_section": "Metro 2 CRRG §2.8",
    }]


def _rule_discharged_balance(tl) -> list:
    """DISCHARGED_BALANCE — FCRA §623(a)(1)(B): balance reported on discharged debt."""
    code = (tl.consumer_information_indicator or "").strip().upper()
    if code not in DISCHARGED_INDICATORS:
        return []
    if tl.balance is None or float(tl.balance) <= 0:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DISCHARGED_BALANCE",
        "rule_name": "Balance Reported on Bankruptcy-Discharged Account",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) has Consumer Information Indicator "
            f"'{code}' ({CONSUMER_INFO_INDICATOR_LABELS.get(code, 'bankruptcy discharge')}) "
            f"but reports balance ${float(tl.balance):,.2f}. A discharged debt eliminates "
            f"personal liability. Reporting a balance may violate FCRA §623(a)(1)(B) and "
            f"the bankruptcy discharge injunction under 11 U.S.C. §524."
        ),
        "fcra_section": "FCRA §623(a)(1)(B); 11 U.S.C. §524 (discharge injunction); Metro 2 CRRG §2.3",
    }]


def _rule_bankruptcy_10yr(tl) -> list:
    """BANKRUPTCY_10YR — FCRA §605(a)(1): bankruptcy past 10-year reporting limit."""
    code = (tl.consumer_information_indicator or "").strip().upper()
    if code not in BANKRUPTCY_INDICATORS:
        return []
    dofd = _parse_date(tl.dofd)
    if dofd is None:
        return []
    delta = (_today() - dofd).days
    if delta > 10 * 365:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "BANKRUPTCY_10YR",
            "rule_name": "Bankruptcy Exceeds 10-Year FCRA Reporting Window",
            "severity": "high",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) carries bankruptcy indicator "
                f"'{code}' ({CONSUMER_INFO_INDICATOR_LABELS.get(code, 'bankruptcy')}) "
                f"with DOFD {tl.dofd} ({delta/365:.1f} years ago). FCRA §605(a)(1) limits "
                f"bankruptcy reporting to 10 years. This account is obsolete and must be "
                f"suppressed from all consumer reports."
            ),
            "fcra_section": "FCRA §605(a)(1) — 10-year bankruptcy limit",
        }]
    return []


def _rule_collection_missing_xo(tl) -> list:
    """COLLECTION_MISSING_XO — Metro 2 CRRG §2.7: collection lacks transfer code XO."""
    status = (tl.payment_status or "").lower()
    acct_type = (tl.account_type or "").lower()
    if status != "collection" and acct_type != "collection":
        return []
    code = (tl.compliance_condition_code or "").strip().upper()
    if code in ("XO", "XF", "XR", "XJ"):
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "COLLECTION_MISSING_XO",
        "rule_name": "Collection Account Missing Metro 2 Transfer Code XO",
        "severity": "low",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is a collection account but lacks "
            f"Compliance Condition Code 'XO' (account sold/transferred to collection agency). "
            f"Metro 2 CRRG §2.7 requires this code to distinguish the collection entry from "
            f"the original creditor tradeline and prevent double-reporting confusion."
        ),
        "fcra_section": "Metro 2 CRRG §2.7; FCRA §623(a)(1)",
    }]


def _rule_dispute_no_xf(tl) -> list:
    """DISPUTE_NO_XF — Metro 2 CRRG §2.7: disputed account missing code XF."""
    remarks = (tl.remarks or "").lower()
    if "dispute" not in remarks:
        return []
    code = (tl.compliance_condition_code or "").strip().upper()
    if code in ("XF", "XH"):
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DISPUTE_NO_XF",
        "rule_name": "Disputed Account Missing Metro 2 Dispute Code XF",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) remarks indicate a dispute but "
            f"Compliance Condition Code is not 'XF'. Metro 2 CRRG §2.7 requires code XF "
            f"when an account is under FCRA §611 dispute. FCRA §623(a)(3) also requires "
            f"furnishers to notify CRAs of direct disputes."
        ),
        "fcra_section": "FCRA §623(a)(3); Metro 2 CRRG §2.7",
    }]


def _rule_date_reported_future(tl) -> list:
    """DATE_REPORTED_FUTURE — Date Reported is in the future: data integrity error."""
    dr = _parse_date(tl.date_reported)
    if dr is None or dr <= _today():
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "DATE_REPORTED_FUTURE",
        "rule_name": "Date Reported Is in the Future",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) Date Reported {tl.date_reported} "
            f"is a future date — a data integrity error in the credit report."
        ),
        "fcra_section": "Metro 2 CRRG §1.4",
    }]


def _rule_open_with_past_close_date(tl) -> list:
    """OPEN_WITH_CLOSE_DATE — active account with a past close_date: status conflict."""
    status = (tl.payment_status or "").lower()
    if status in ("closed", "paid", "charge_off", "collection"):
        return []
    close_date = _parse_date(tl.close_date)
    if close_date is None or close_date >= _today():
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "OPEN_WITH_CLOSE_DATE",
        "rule_name": "Open Account Has a Past Close Date — Status Conflict",
        "severity": "medium",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) status '{tl.payment_status}' "
            f"(not closed) but close_date={tl.close_date}. Metro 2 CRRG §1.6 requires "
            f"account status to accurately reflect current standing."
        ),
        "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §1.6",
    }]


def _rule_chargeoff_growing_balance(tl) -> list:
    """CHARGEOFF_GROWING_BALANCE — charge-off balance exceeds original amount (post-CO fees)."""
    if (tl.payment_status or "").lower() != "charge_off":
        return []
    if tl.balance is None or tl.high_balance is None:
        return []
    if float(tl.high_balance) <= 0:
        return []
    if float(tl.balance) > float(tl.high_balance) * 1.05:
        pct = (float(tl.balance) / float(tl.high_balance) - 1) * 100
        return [{
            "tradeline_id": tl.id,
            "rule_code": "CHARGEOFF_GROWING_BALANCE",
            "rule_name": "Charge-Off Balance Exceeds Original Charge-Off Amount",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) charge-off balance "
                f"${float(tl.balance):,.2f} is {pct:.0f}% above high balance "
                f"${float(tl.high_balance):,.2f}. Interest/fees accruing after charge-off "
                f"must be disclosed. Undisclosed fee accrual may violate FCRA §623(a)(1)(A) "
                f"and FDCPA §1692f (unfair collection means)."
            ),
            "fcra_section": "FCRA §623(a)(1)(A); FDCPA §1692f; Metro 2 CRRG §2.3",
        }]
    return []


def _rule_collection_excessive_balance(tl) -> list:
    """COLLECTION_EXCESSIVE_BALANCE — FDCPA §1692f: collection balance >40% over original."""
    status = (tl.payment_status or "").lower()
    acct_type = (tl.account_type or "").lower()
    if status != "collection" and acct_type != "collection":
        return []
    if tl.balance is None or tl.high_balance is None or float(tl.high_balance) <= 0:
        return []
    ratio = float(tl.balance) / float(tl.high_balance)
    if ratio > 1.40:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "COLLECTION_EXCESSIVE_BALANCE",
            "rule_name": "Collection Balance Exceeds Original Debt by >40% (FDCPA §1692f)",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) collection balance "
                f"${float(tl.balance):,.2f} is {(ratio-1)*100:.0f}% above high balance "
                f"${float(tl.high_balance):,.2f}. FDCPA §1692f prohibits collecting amounts "
                f"not expressly authorized by the original agreement or law. "
                f"Issue a FDCPA §1692g debt validation request."
            ),
            "fcra_section": "FDCPA §1692f (unfair means); FDCPA §1692g (validation)",
        }]
    return []


def _rule_paid_collection_nonzero(tl) -> list:
    """PAID_COLLECTION_NONZERO — paid collection still reporting a balance."""
    status = (tl.payment_status or "").lower()
    acct_type = (tl.account_type or "").lower()
    if acct_type != "collection":
        return []
    if status not in ("paid", "closed"):
        return []
    if tl.balance is None or float(tl.balance) <= 0:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "PAID_COLLECTION_NONZERO",
        "rule_name": "Paid Collection Account Still Shows Positive Balance",
        "severity": "high",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is a '{status}' collection "
            f"but reports balance ${float(tl.balance):,.2f}. A paid collection must report "
            f"$0 balance per Metro 2 CRRG §2.3. Inaccurate balance on a paid account "
            f"violates FCRA §623(a)(1)."
        ),
        "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.3",
    }]


def _rule_settled_full_balance(tl) -> list:
    """SETTLED_FULL_BALANCE — settled account may be reporting full (not settled) balance."""
    remarks = (tl.remarks or "").lower()
    if "settled" not in remarks and "partial" not in remarks:
        return []
    if tl.balance is None or tl.high_balance is None:
        return []
    if float(tl.high_balance) <= 0 or float(tl.balance) <= 0:
        return []
    ratio = float(tl.balance) / float(tl.high_balance)
    if ratio > 0.90:
        return [{
            "tradeline_id": tl.id,
            "rule_code": "SETTLED_FULL_BALANCE",
            "rule_name": "Settled Account May Show Full Balance Instead of Settled Amount",
            "severity": "medium",
            "description": (
                f"Account '{tl.creditor_name}' ({tl.bureau}) remarks indicate settlement "
                f"but balance ${float(tl.balance):,.2f} is {ratio*100:.0f}% of high balance "
                f"${float(tl.high_balance):,.2f}. A settled account should report the settled "
                f"amount (not full balance) with Metro 2 Special Comment Code 'AU'. "
                f"Incorrect balance reporting violates FCRA §623(a)(1)."
            ),
            "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.6 (Special Comment AU)",
        }]
    return []


def _rule_past_due_missing_derogatory(tl) -> list:
    """PAST_DUE_NOT_DEROGATORY — has positive past-due amount but not marked derogatory."""
    if tl.past_due_amount is None or float(tl.past_due_amount) <= 0:
        return []
    if tl.derogatory:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "PAST_DUE_NOT_DEROGATORY",
        "rule_name": "Account Has Past-Due Amount but Not Flagged Derogatory",
        "severity": "info",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) reports past_due_amount="
            f"${float(tl.past_due_amount):,.2f} but is not marked derogatory. "
            f"An account with a positive past-due balance should typically be flagged "
            f"as derogatory per Metro 2 reporting standards."
        ),
        "fcra_section": "Metro 2 CRRG §2.4",
    }]


def _rule_credit_limit_missing_revolving(tl) -> list:
    """CREDIT_LIMIT_MISSING — revolving account has no credit_limit (Metro 2 field required)."""
    acct_type = (tl.account_type or "").lower()
    if "credit_card" not in acct_type and "revolving" not in acct_type:
        return []
    if tl.credit_limit is not None and float(tl.credit_limit) > 0:
        return []
    return [{
        "tradeline_id": tl.id,
        "rule_code": "CREDIT_LIMIT_MISSING",
        "rule_name": "Revolving Account Missing Credit Limit",
        "severity": "low",
        "description": (
            f"Account '{tl.creditor_name}' ({tl.bureau}) is a revolving/credit card account "
            f"with no credit_limit reported. Metro 2 CRRG §2.5 requires furnishers to report "
            f"the credit limit on all open-end revolving accounts. Missing credit limit "
            f"inflates the apparent utilization ratio, potentially harming credit scoring."
        ),
        "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.5",
    }]


# ── Cross-bureau consistency rules ───────────────────────────────────────────
# These rules operate on the full list of tradelines to detect inter-bureau issues.

def _cross_bureau_rules(tradelines: list) -> list[dict]:
    """
    Group tradelines by (creditor_name, account_number_last4) and run
    cross-bureau Metro 2 consistency checks.
    """
    findings = []

    groups: dict[str, list] = {}
    for tl in tradelines:
        name = (tl.creditor_name or "").strip().lower()
        last4 = (tl.account_number_last4 or "").strip()
        if not name:
            continue
        key = f"{name}||{last4}"
        groups.setdefault(key, []).append(tl)

    for key, group in groups.items():
        if len(group) < 2:
            continue
        creditor = group[0].creditor_name or "Unknown"
        last4 = group[0].account_number_last4 or ""
        label = f"'{creditor}' (xxxx-{last4})"

        # ── Payment status consistency
        statuses = list({(tl.payment_status or "").lower() for tl in group})
        if len(statuses) > 1:
            detail = ", ".join(f"{tl.bureau}={tl.payment_status}" for tl in group)
            findings.append({
                "tradeline_id": None,
                "rule_code": "CROSS_STATUS_MISMATCH",
                "rule_name": "Inconsistent Payment Status Across Bureaus",
                "severity": "high",
                "description": (
                    f"{label} reports different payment statuses: {detail}. "
                    f"All bureaus must receive identical Metro 2 Payment Rating data. "
                    f"Discrepancies indicate selective or inaccurate furnisher reporting "
                    f"in violation of FCRA §623(a)(1)."
                ),
                "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.1",
            })

        # ── Balance consistency (>10% variance = concern)
        balances = [(tl.bureau, float(tl.balance)) for tl in group if tl.balance is not None]
        if len(balances) >= 2:
            vals = [v for _, v in balances]
            if max(vals) > 0 and (max(vals) - min(vals)) / max(vals) > 0.10:
                detail = ", ".join(f"{b}=${v:,.2f}" for b, v in balances)
                findings.append({
                    "tradeline_id": None,
                    "rule_code": "CROSS_BALANCE_MISMATCH",
                    "rule_name": "Balance Inconsistency Across Bureaus (>10% Variance)",
                    "severity": "medium",
                    "description": (
                        f"{label} reports materially different balances: {detail}. "
                        f"Metro 2 requires furnishers to submit the same balance to all bureaus. "
                        f">10% variance suggests stale or selective reporting under FCRA §623(a)(1)."
                    ),
                    "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.3",
                })

        # ── DOFD consistency — different DOFD = re-aging
        dodfs = [(tl.bureau, tl.dofd) for tl in group if tl.dofd]
        if len(dodfs) >= 2:
            unique_dodfs = list({d for _, d in dodfs})
            if len(unique_dodfs) > 1:
                detail = ", ".join(f"{b}={d}" for b, d in dodfs)
                findings.append({
                    "tradeline_id": None,
                    "rule_code": "CROSS_DOFD_MISMATCH",
                    "rule_name": "Inconsistent DOFD Across Bureaus — Strong Re-Aging Indicator",
                    "severity": "high",
                    "description": (
                        f"{label} has different DOFD dates across bureaus: {detail}. "
                        f"DOFD must be identical on all bureaus — it is set once and never changed. "
                        f"Different DOFDs strongly indicate re-aging, extending the 7-year "
                        f"FCRA §605(a) window improperly."
                    ),
                    "fcra_section": "FCRA §605(a); FCRA §623(a)(1); Metro 2 CRRG §1.5",
                })

        # ── Derogatory flag inconsistency
        derog = [(tl.bureau, tl.derogatory) for tl in group]
        if len(list({d for _, d in derog})) > 1:
            detail = ", ".join(f"{b}={'neg' if d else 'OK'}" for b, d in derog)
            findings.append({
                "tradeline_id": None,
                "rule_code": "CROSS_DEROGATORY_MISMATCH",
                "rule_name": "Derogatory Status Inconsistent Across Bureaus",
                "severity": "medium",
                "description": (
                    f"{label} is derogatory on some bureaus but not others: {detail}. "
                    f"Selective negative reporting violates FCRA §623(a)(1) accuracy requirements."
                ),
                "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §2.1",
            })

        # ── Potential duplicate debt: OC + collection agency reporting same debt
        acct_types = [(tl.bureau, (tl.account_type or "").lower()) for tl in group]
        type_set = {t for _, t in acct_types}
        if "collection" in type_set and len(type_set) > 1:
            detail = ", ".join(f"{b}={t}" for b, t in acct_types)
            findings.append({
                "tradeline_id": None,
                "rule_code": "POTENTIAL_DUPLICATE_DEBT",
                "rule_name": "Potential Duplicate Debt — Original Creditor + Collection Agency",
                "severity": "high",
                "description": (
                    f"{label} appears reported by both original creditor and collection agency: "
                    f"{detail}. Metro 2 CRRG §4.1 and CFPB guidance prohibit double-reporting "
                    f"the same debt. Duplicate reporting magnifies negative credit impact and "
                    f"may constitute inaccurate reporting under FCRA §623(a)(1)."
                ),
                "fcra_section": "FCRA §623(a)(1); Metro 2 CRRG §4.1 — duplicate reporting prohibition",
            })

        # ── Selective bureau reporting of derogatory accounts (info)
        derogatory_on_any = any(tl.derogatory for tl in group)
        if derogatory_on_any:
            bureaus_present = {(tl.bureau or "").lower() for tl in group}
            all_major = {"experian", "equifax", "transunion"}
            missing = all_major - bureaus_present
            if missing:
                findings.append({
                    "tradeline_id": None,
                    "rule_code": "SELECTIVE_BUREAU_REPORTING",
                    "rule_name": "Derogatory Account Missing from One or More Major Bureaus",
                    "severity": "info",
                    "description": (
                        f"{label} is derogatory on {', '.join(bureaus_present)} but not found on "
                        f"{', '.join(missing)}. While furnishers need not report to all bureaus, "
                        f"selective negative reporting warrants investigation."
                    ),
                    "fcra_section": "FCRA §623(a)(1) — accuracy (informational)",
                })

    return findings


# ── Master rule registry ─────────────────────────────────────────────────────

_INDIVIDUAL_RULES = [
    # DOFD / obsolescence rules
    _rule_dofd_7yr,
    _rule_dofd_approaching,
    _rule_missing_dofd,
    _rule_dofd_future,
    _rule_dofd_after_reported,
    _rule_dofd_before_open,
    # Balance / payment fields
    _rule_balance_exceeds_high,
    _rule_past_due_on_current,
    _rule_zero_past_due_on_derogatory,
    _rule_past_due_missing_derogatory,
    _rule_credit_limit_missing_revolving,
    # Status / reporting fields
    _rule_stale_reporting,
    _rule_payment_rating_mismatch,
    _rule_invalid_payment_rating,
    _rule_open_with_past_close_date,
    # Metro 2 code validation
    _rule_invalid_compliance_code,
    _rule_invalid_consumer_info,
    # Bankruptcy
    _rule_discharged_balance,
    _rule_bankruptcy_10yr,
    # FDCPA / collection-specific
    _rule_collection_missing_xo,
    _rule_dispute_no_xf,
    _rule_date_reported_future,
    _rule_chargeoff_growing_balance,
    _rule_collection_excessive_balance,
    _rule_paid_collection_nonzero,
    _rule_settled_full_balance,
]


def run_metro2_rules(tradelines: list) -> list[dict]:
    """
    Run the full Metro 2 / FCRA compliance audit.

    Accepts a list of Tradeline ORM objects.
    Returns finding dicts: tradeline_id, rule_code, rule_name, severity, description, fcra_section.
    """
    findings: list[dict] = []

    for tl in tradelines:
        for rule_fn in _INDIVIDUAL_RULES:
            try:
                findings.extend(rule_fn(tl))
            except Exception:
                pass

    try:
        findings.extend(_cross_bureau_rules(tradelines))
    except Exception:
        pass

    return findings
