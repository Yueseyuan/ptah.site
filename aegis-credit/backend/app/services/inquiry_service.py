"""Inquiry Analysis Rules Engine -- pure Python, no external deps."""
from __future__ import annotations

from datetime import datetime, timedelta
from collections import defaultdict


def _parse_date(date_str):
    """Parse a date string to a datetime object."""
    if not date_str:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    return None


def run_inquiry_analysis(inquiries):
    """
    Run inquiry consistency and anomaly rules.

    Each inquiry in inquiries is a dict with keys:
      bureau, inquiry_type, subscriber_name, inquiry_date, purpose

    Returns a list of finding dicts:
      {rule_code, rule_name, severity, description, fcra_section}
    """
    findings = []

    # Group by bureau -> subscriber -> list of inquiry dicts
    bureau_subscriber = defaultdict(lambda: defaultdict(list))
    for inq in inquiries:
        bureau = (inq.get("bureau") or "unknown").lower()
        subscriber = (inq.get("subscriber_name") or "").strip().lower()
        if subscriber:
            bureau_subscriber[bureau][subscriber].append(inq)

    # -- INQ-001: Duplicate Inquiry (same subscriber, same bureau, within 30 days)
    try:
        for bureau, subscribers in bureau_subscriber.items():
            for subscriber, inq_list in subscribers.items():
                dates = []
                for inq in inq_list:
                    d = _parse_date(inq.get("inquiry_date"))
                    if d:
                        dates.append(d)
                if len(dates) < 2:
                    continue
                dates.sort()
                for i in range(len(dates) - 1):
                    if (dates[i + 1] - dates[i]) <= timedelta(days=30):
                        n = len(dates)
                        findings.append({
                            "rule_code": "INQ-001",
                            "rule_name": "Duplicate Inquiry",
                            "severity": "medium",
                            "description": (
                                "Potential duplicate inquiry: {} appears {} time(s) on {} within 30 days. "
                                "Review recommended.".format(
                                    subscriber.title(), n, bureau.title()
                                )
                            ),
                            "fcra_section": "FCRA §604",
                        })
                        break
    except Exception:
        pass

    # -- INQ-002: Inquiry Conflict (same subscriber on multiple bureaus, different dates)
    try:
        subscriber_bureaus: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
        for inq in inquiries:
            bureau = (inq.get("bureau") or "unknown").lower()
            subscriber = (inq.get("subscriber_name") or "").strip().lower()
            date_str = inq.get("inquiry_date") or ""
            if subscriber and date_str:
                subscriber_bureaus[subscriber][bureau].add(date_str)

        for subscriber, bureau_dates in subscriber_bureaus.items():
            if len(bureau_dates) >= 2:
                unique_dates = {d for dates in bureau_dates.values() for d in dates}
                if len(unique_dates) > 1:
                    findings.append({
                        "rule_code": "INQ-002",
                        "rule_name": "Inquiry Conflict",
                        "severity": "low",
                        "description": (
                            "Inquiry date for {} differs across bureaus. "
                            "Review recommended.".format(subscriber.title())
                        ),
                        "fcra_section": "FCRA §604",
                    })
    except Exception:
        pass

    # -- INQ-003: Unusual Inquiry Activity (>6 hard inquiries on a single bureau)
    try:
        bureau_hard_count = defaultdict(int)
        for inq in inquiries:
            bureau = (inq.get("bureau") or "unknown").lower()
            inq_type = (inq.get("inquiry_type") or "hard").lower()
            if inq_type == "hard":
                bureau_hard_count[bureau] += 1

        for bureau, count in bureau_hard_count.items():
            if count > 6:
                findings.append({
                    "rule_code": "INQ-003",
                    "rule_name": "Unusual Inquiry Activity",
                    "severity": "medium",
                    "description": (
                        "High volume of hard inquiries detected on {}: {} inquiries. "
                        "Human review recommended.".format(bureau.title(), count)
                    ),
                    "fcra_section": "FCRA §604",
                })
    except Exception:
        pass

    return findings
