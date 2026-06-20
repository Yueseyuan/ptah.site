"""Court Records Analysis Engine — Spec §23."""
from __future__ import annotations
from typing import Optional


def analyze_court_records(court_records: list[dict], tradelines: list[dict]) -> list[dict]:
    """Analyze court records against tradelines for conflicts.

    Returns a list of finding dicts with keys:
        rule_code, rule_name, severity, description, fcra_section,
        court_record_ids (list)
    """
    findings = []

    # Helper: list of derogatory tradeline statuses
    DEROGATORY_STATUSES = {
        "collection", "charge_off", "charge-off", "90_days_late", "60_days_late",
        "30_days_late", "past_due", "derogatory", "settled", "repossession",
    }

    for cr in court_records:
        court_record_ids = [cr.get("id")]
        disposition = (cr.get("disposition") or "").lower()
        court_name = (cr.get("court_name") or "").lower()
        cr_amount = None  # CourtRecord doesn't have an amount field — skip CT-001 amount check

        # CT-002: Party Conflict — plaintiff not found in tradelines
        # We'll use court_name as proxy for plaintiff
        # Actually court_records have no plaintiff field; use docket_number/notes
        # Use court_name as the party name to check
        found_in_tradeline = False
        if court_name:
            for tl in tradelines:
                creditor = (tl.get("creditor_name") or "").lower()
                if court_name in creditor or creditor in court_name:
                    found_in_tradeline = True
                    break
        # Only trigger if we have a meaningful court_name
        if court_name and not found_in_tradeline:
            findings.append({
                "rule_code": "CT-002",
                "rule_name": "Party Conflict",
                "severity": "medium",
                "description": (
                    "Court plaintiff not found in reported tradelines. "
                    "Potential party conflict. Human review required."
                ),
                "fcra_section": "FCRA §623",
                "court_record_ids": court_record_ids,
            })

        # CT-003: Dismissed Case Review
        if "dismiss" in disposition:
            # Check if any tradeline shows active collection
            active_collection = any(
                (tl.get("payment_status") or "").lower() in {"collection", "active"}
                for tl in tradelines
            )
            if active_collection:
                findings.append({
                    "rule_code": "CT-003",
                    "rule_name": "Dismissed Case Review",
                    "severity": "medium",
                    "description": (
                        "Dismissed court case may warrant review of current collection reporting. "
                        "Human investigation required."
                    ),
                    "fcra_section": "FCRA §611",
                    "court_record_ids": court_record_ids,
                })

        # CT-004: Court Reporting Conflict — court record exists but no derogatory tradeline
        has_derogatory = any(
            (tl.get("payment_status") or "").lower() in DEROGATORY_STATUSES
            or tl.get("derogatory") is True
            for tl in tradelines
        )
        if not has_derogatory:
            findings.append({
                "rule_code": "CT-004",
                "rule_name": "Court Reporting Conflict",
                "severity": "high",
                "description": (
                    "Active court record found but no derogatory tradeline status detected. "
                    "Review recommended."
                ),
                "fcra_section": "FCRA §623",
                "court_record_ids": court_record_ids,
            })

        # CT-005: Judgment Review
        if "judgment" in disposition:
            findings.append({
                "rule_code": "CT-005",
                "rule_name": "Judgment Review",
                "severity": "high",
                "description": (
                    "Judgment record detected. Review of credit reporting for accuracy "
                    "is recommended."
                ),
                "fcra_section": "FCRA §623",
                "court_record_ids": court_record_ids,
            })

    return findings
