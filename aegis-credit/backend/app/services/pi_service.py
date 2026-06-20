"""Personal Information Rules Engine -- pure Python, no external deps."""
from __future__ import annotations

import json


def _parse_json_list(value):
    """Parse a list stored as JSON array or semicolon-separated plain text."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(v).strip() for v in parsed if str(v).strip()]
    except Exception:
        pass
    # Fall back to semicolon-separated plain text
    return [s.strip() for s in str(value).split(';') if s.strip()]


def _extract_last_name(full_name):
    """Best-effort extract of the last word as last name."""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    return parts[-1].lower() if parts else ""


def run_pi_analysis(pi_records):
    """
    Run personal-information consistency rules across bureau records.

    Each record in pi_records is a dict with keys:
      bureau, current_name, aliases (JSON str or list), current_address,
      previous_addresses (JSON str or list), current_employer,
      previous_employers (JSON str or list), phone_numbers (JSON str or list),
      dob, ssn_last4

    Returns a list of finding dicts:
      {rule_code, rule_name, severity, description, fcra_section}
    """
    findings = []
    triggered_rules = []

    # -- PI-001: Unknown Address
    try:
        bureau_addresses = {}
        for rec in pi_records:
            bureau = rec.get("bureau", "unknown")
            addrs = []
            if rec.get("current_address"):
                addrs.append(rec["current_address"].strip().lower())
            prev = rec.get("previous_addresses")
            if isinstance(prev, list):
                addrs += [a.strip().lower() for a in prev if a and a.strip()]
            else:
                addrs += [a.strip().lower() for a in _parse_json_list(prev) if a.strip()]
            bureau_addresses[bureau] = set(addrs)

        all_bureaus = list(bureau_addresses.keys())
        for bureau, addrs in bureau_addresses.items():
            for addr in addrs:
                if not addr:
                    continue
                other_bureaus_have = any(
                    addr in bureau_addresses[b]
                    for b in all_bureaus
                    if b != bureau
                )
                if not other_bureaus_have:
                    findings.append({
                        "rule_code": "PI-001",
                        "rule_name": "Unknown Address",
                        "severity": "medium",
                        "description": (
                            "Address appears only on {}. "
                            "Potential unknown address. Human review recommended.".format(bureau)
                        ),
                        "fcra_section": "FCRA §611",
                    })
                    triggered_rules.append("PI-001")
                    break
    except Exception:
        pass

    # -- PI-002: Name Conflict
    try:
        bureau_names = {}
        for rec in pi_records:
            bureau = rec.get("bureau", "unknown")
            name = (rec.get("current_name") or "").strip().lower()
            if name:
                bureau_names[bureau] = name

        unique_names = set(bureau_names.values())
        if len(unique_names) > 1:
            names_display = ", ".join(sorted(unique_names))
            findings.append({
                "rule_code": "PI-002",
                "rule_name": "Name Conflict",
                "severity": "high",
                "description": (
                    "Consumer name differs across bureaus: {}. "
                    "Potential inconsistency. Human review required.".format(names_display)
                ),
                "fcra_section": "FCRA §623",
            })
            triggered_rules.append("PI-002")
    except Exception:
        pass

    # -- PI-003: Employer Conflict
    try:
        bureau_employers = {}
        for rec in pi_records:
            bureau = rec.get("bureau", "unknown")
            employer = (rec.get("current_employer") or "").strip().lower()
            if employer:
                bureau_employers[bureau] = employer

        unique_employers = set(bureau_employers.values())
        if len(unique_employers) > 1:
            findings.append({
                "rule_code": "PI-003",
                "rule_name": "Employer Conflict",
                "severity": "low",
                "description": "Current employer differs across bureaus. Review recommended.",
                "fcra_section": "FCRA §611",
            })
            triggered_rules.append("PI-003")
    except Exception:
        pass

    # -- PI-006: Alias Inconsistency (one bureau has alias others don't)
    try:
        bureau_aliases: dict[str, set] = {}
        for rec in pi_records:
            bureau = rec.get("bureau", "unknown")
            aliases = rec.get("aliases")
            if isinstance(aliases, list):
                alias_list = [a.strip().lower() for a in aliases if a and a.strip()]
            else:
                alias_list = [a.lower() for a in _parse_json_list(aliases)]
            bureau_aliases[bureau] = set(alias_list)

        all_aliases = set(a for s in bureau_aliases.values() for a in s)
        for alias in all_aliases:
            bureaus_with = [b for b, s in bureau_aliases.items() if alias in s]
            bureaus_without = [b for b, s in bureau_aliases.items() if alias not in s]
            if bureaus_with and bureaus_without:
                findings.append({
                    "rule_code": "PI-006",
                    "rule_name": "Alias Inconsistency Across Bureaus",
                    "severity": "medium",
                    "description": (
                        "Alias '{}' appears on {} but is missing from {}. "
                        "Inconsistent alias reporting may indicate a mixed file or "
                        "selective furnisher reporting under FCRA §623(a)(1).".format(
                            alias.title(),
                            ", ".join(bureaus_with),
                            ", ".join(bureaus_without),
                        )
                    ),
                    "fcra_section": "FCRA §611; FCRA §623(a)(1)",
                })
                triggered_rules.append("PI-006")
    except Exception:
        pass

    # -- PI-004: Mixed File Indicator
    try:
        all_last_names = set()
        for rec in pi_records:
            name = (rec.get("current_name") or "").strip()
            last = _extract_last_name(name)
            if last:
                all_last_names.add(last)
            aliases = rec.get("aliases")
            if isinstance(aliases, list):
                alias_list = aliases
            else:
                alias_list = _parse_json_list(aliases)
            for alias in alias_list:
                alias_last = _extract_last_name(alias)
                if alias_last:
                    all_last_names.add(alias_last)

        if len(all_last_names) > 2:
            findings.append({
                "rule_code": "PI-004",
                "rule_name": "Mixed File Indicator",
                "severity": "high",
                "description": (
                    "Multiple distinct last names detected. "
                    "Potential mixed-file indicator. Human investigation required. "
                    "Attorney review recommended."
                ),
                "fcra_section": "FCRA §611",
            })
            triggered_rules.append("PI-004")
    except Exception:
        pass

    # -- PI-005: Identity Conflict (2+ rules triggered)
    try:
        if len(set(triggered_rules)) >= 2:
            findings.append({
                "rule_code": "PI-005",
                "rule_name": "Identity Conflict",
                "severity": "high",
                "description": (
                    "Multiple personal information fields conflict across bureaus. "
                    "Potential identity issue. Human investigation required."
                ),
                "fcra_section": "FCRA §611",
            })
    except Exception:
        pass

    return findings
