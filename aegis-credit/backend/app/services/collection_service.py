"""Collection Account Review Engine — Spec §20."""
from __future__ import annotations
from datetime import date, datetime
from collections import defaultdict
from typing import Optional

KNOWN_DEBT_BUYERS = [
    "lvnv funding", "midland credit", "portfolio recovery", "resurgent",
    "cavalry portfolio", "jefferson capital", "asset acceptance",
    "encore capital", "jdb partners", "unifin", "convergent",
    "radius global", "national collegiate", "first collection",
    "credit corp solutions", "velocity investments", "asta funding",
]


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


def _is_collection(tl: dict) -> bool:
    acct_type = (tl.get("account_type") or "").lower()
    status = (tl.get("payment_status") or "").lower()
    return "collection" in acct_type or "collection" in status


def analyze_collection_accounts(tradelines: list[dict]) -> list[dict]:
    """Analyze tradelines for collection account issues.

    Returns a list of finding dicts with keys:
        rule_code, rule_name, severity, description, fcra_section,
        tradeline_ids (list), bureaus_affected (list)
    """
    findings = []
    collection_tls = [tl for tl in tradelines if _is_collection(tl)]

    # COL-001: Known Debt Buyer
    for tl in collection_tls:
        creditor = (tl.get("creditor_name") or "").lower()
        for pattern in KNOWN_DEBT_BUYERS:
            if pattern in creditor:
                findings.append({
                    "rule_code": "COL-001",
                    "rule_name": "Known Debt Buyer",
                    "severity": "medium",
                    "description": (
                        f"Account appears to be held by a debt buyer ({tl.get('creditor_name')}). "
                        "Original creditor chain and assignment documentation may warrant review. "
                        "Human investigation required."
                    ),
                    "fcra_section": "FCRA §623",
                    "tradeline_ids": [tl.get("id")],
                    "bureaus_affected": [tl.get("bureau")],
                })
                break

    # COL-002: Collection Balance Discrepancy (same creditor+account across bureaus)
    # Group by (creditor_name, account_number_last4)
    grouped = defaultdict(list)
    for tl in collection_tls:
        key = (
            (tl.get("creditor_name") or "").lower().strip(),
            (tl.get("account_number_last4") or "").strip(),
        )
        grouped[key].append(tl)

    for key, group in grouped.items():
        if len(group) < 2:
            continue
        balances = [tl.get("balance") for tl in group if tl.get("balance") is not None]
        if len(balances) >= 2:
            if max(balances) - min(balances) > 10:
                bureaus = [tl.get("bureau") for tl in group]
                findings.append({
                    "rule_code": "COL-002",
                    "rule_name": "Collection Balance Discrepancy",
                    "severity": "high",
                    "description": (
                        "Collection account balance discrepancy detected across bureaus. "
                        "Review recommended."
                    ),
                    "fcra_section": "FCRA §623",
                    "tradeline_ids": [tl.get("id") for tl in group],
                    "bureaus_affected": bureaus,
                })

    # COL-003: Stale Collection (DOFD > 7 years ago)
    for tl in collection_tls:
        dofd = _parse_date(tl.get("dofd"))
        if dofd is None:
            continue
        delta = (_today() - dofd).days
        if delta > 7 * 365:
            findings.append({
                "rule_code": "COL-003",
                "rule_name": "Stale Collection",
                "severity": "high",
                "description": (
                    "Collection account DOFD indicates this may be outside the 7-year FCRA "
                    "reporting window. Human review required. Potential inconsistency detected."
                ),
                "fcra_section": "FCRA §605(a)(4)",
                "tradeline_ids": [tl.get("id")],
                "bureaus_affected": [tl.get("bureau")],
            })

    # COL-004: Duplicate Collection (same original balance+creditor from multiple collectors)
    # Group collection tradelines by (account_number_last4, balance)
    dup_groups = defaultdict(list)
    for tl in collection_tls:
        acct = (tl.get("account_number_last4") or "").strip()
        if not acct:
            continue
        key = acct
        dup_groups[key].append(tl)

    for key, group in dup_groups.items():
        creditors = set((tl.get("creditor_name") or "").lower().strip() for tl in group)
        if len(creditors) > 1:
            findings.append({
                "rule_code": "COL-004",
                "rule_name": "Duplicate Collection",
                "severity": "high",
                "description": (
                    "Potential duplicate collection account detected. Same underlying debt "
                    "may be reported by multiple collectors. Review recommended."
                ),
                "fcra_section": "FCRA §623",
                "tradeline_ids": [tl.get("id") for tl in group],
                "bureaus_affected": list(set(tl.get("bureau") for tl in group)),
            })

    # COL-005: Missing DOFD on Collection
    for tl in collection_tls:
        dofd = tl.get("dofd")
        if not dofd or not str(dofd).strip():
            findings.append({
                "rule_code": "COL-005",
                "rule_name": "Missing DOFD on Collection",
                "severity": "medium",
                "description": (
                    "Date of First Delinquency missing on collection account. "
                    "Required for FCRA §605 compliance. Review recommended."
                ),
                "fcra_section": "FCRA §605",
                "tradeline_ids": [tl.get("id")],
                "bureaus_affected": [tl.get("bureau")],
            })

    return findings
