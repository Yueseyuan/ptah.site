import os
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AegisCase, AegisClient, GeneratedReport, Finding, StrategyItem, Tradeline, Outcome, DisputeRound
from app.config import settings

router = APIRouter(prefix="/api/report-generator", tags=["report_generator"])

_BUREAU_ADDRESS = {
    "experian":   "Experian Information Solutions, Inc.\nP.O. Box 4500\nAllen, TX 75013",
    "equifax":    "Equifax Information Services LLC\nP.O. Box 740256\nAtlanta, GA 30374",
    "transunion": "TransUnion LLC\nConsumer Dispute Center\nP.O. Box 2000\nChester, PA 19016",
    "innovis":    "Innovis Consumer Assistance\nPO Box 530000\nColumbus, OH 43218",
}

_STATE_SOL = {
    "SC": ("3 years", "S.C. Code Ann. §15-3-530(1)"),
    "MD": ("3 years", "Md. Code, Cts. & Jud. Proc. §5-101"),
    "MI": ("6 years", "Mich. Comp. Laws §600.5807"),
    "NY": ("6 years", "N.Y. C.P.L.R. §213"),
    "CA": ("4 years", "Cal. Civ. Proc. Code §337"),
    "TX": ("4 years", "Tex. Civ. Prac. & Rem. Code §16.004"),
    "FL": ("5 years", "Fla. Stat. §95.11(2)"),
    "GA": ("6 years", "O.C.G.A. §9-3-24"),
    "NC": ("3 years", "N.C. Gen. Stat. §1-52"),
    "VA": ("5 years", "Va. Code §8.01-246"),
    "PA": ("4 years", "42 Pa. C.S. §5525"),
    "OH": ("6 years", "Ohio Rev. Code §2305.07"),
    "IL": ("5 years", "735 ILCS 5/13-205"),
    "NJ": ("6 years", "N.J. Stat. §2A:14-1"),
    "WA": ("6 years", "Wash. Rev. Code §4.16.040"),
    "AZ": ("6 years", "Ariz. Rev. Stat. §12-548"),
    "CO": ("6 years", "Colo. Rev. Stat. §13-80-103.5"),
    "TN": ("6 years", "Tenn. Code §28-3-109"),
    "AL": ("6 years", "Ala. Code §6-2-34"),
    "MN": ("6 years", "Minn. Stat. §541.05"),
}

_STATE_AG = {
    "SC": "South Carolina Attorney General",
    "MD": "Maryland Attorney General",
    "MI": "Michigan Attorney General",
    "NY": "New York Attorney General",
    "CA": "California Attorney General",
    "TX": "Texas Attorney General",
    "FL": "Florida Attorney General",
    "GA": "Georgia Attorney General",
    "NC": "North Carolina Attorney General",
    "VA": "Virginia Attorney General",
    "PA": "Pennsylvania Attorney General",
    "OH": "Ohio Attorney General",
    "IL": "Illinois Attorney General",
    "NJ": "New Jersey Attorney General",
    "WA": "Washington Attorney General",
    "AZ": "Arizona Attorney General",
    "CO": "Colorado Attorney General",
    "TN": "Tennessee Attorney General",
    "AL": "Alabama Attorney General",
    "MN": "Minnesota Attorney General",
}

_STATE_UDAP = {
    "SC": ("South Carolina Unfair Trade Practices Act (SCUTPA)", "S.C. Code §39-5-20"),
    "MD": ("Maryland Consumer Protection Act (MCPA)", "Md. Code Com. Law §13-301; Maryland Consumer Debt Collection Act (MCDCA), Md. Code Com. Law §14-202"),
    "MI": ("Michigan Consumer Protection Act", "Mich. Comp. Laws §445.903"),
    "NY": ("New York Consumer Protection Act", "N.Y. Gen. Bus. Law §349"),
    "CA": ("California Unfair Competition Law", "Cal. Bus. & Prof. Code §17200"),
    "FL": ("Florida Unfair and Deceptive Trade Practices Act", "Fla. Stat. §501.201"),
    "GA": ("Georgia Fair Business Practices Act", "O.C.G.A. §10-1-390"),
    "NC": ("North Carolina Unfair and Deceptive Trade Practices Act", "N.C. Gen. Stat. §75-1.1"),
    "VA": ("Virginia Consumer Protection Act", "Va. Code §59.1-196"),
    "PA": ("Pennsylvania UTPCPL", "73 P.S. §201-1"),
    "OH": ("Ohio Consumer Sales Practices Act", "Ohio Rev. Code §1345.01"),
    "TX": ("Texas Deceptive Trade Practices Act", "Tex. Bus. & Com. Code §17.41"),
    "IL": ("Illinois Consumer Fraud Act", "815 ILCS 505/1"),
    "NJ": ("New Jersey Consumer Fraud Act", "N.J. Stat. §56:8-1"),
    "WA": ("Washington Consumer Protection Act", "Wash. Rev. Code §19.86.020"),
}

_STATE_EVIDENCE = {
    "SC": "S.C. Code §19-1-90",
    "MD": "Md. Rules 5-603",
    "MI": "MRE 603",
    "NY": "NY CPLR §2309",
    "CA": "Cal. Code Civ. Proc. §2015.5",
    "FL": "Fla. Stat. §92.525",
    "GA": "O.C.G.A. §24-13-27",
    "NC": "N.C. Gen. Stat. §11-2",
    "VA": "Va. Code §8.01-413",
    "PA": "42 Pa. C.S. §6132",
    "TX": "Tex. Civ. Prac. & Rem. Code §132.001",
}

_ENFORCEMENT_ACTIONS = [
    "CFPB v. Equifax (2025) — $15M penalty for improper dispute handling",
    "CFPB v. Experian (2025) — alleged sham investigations",
    "FTC/CFPB v. TransUnion (2023) — $15M settlement for accuracy failures",
    "TransUnion (2025) — $2.5M settlement for retaining deleted consumer data",
]

_SEP = "─" * 70


def _client_addr_block(client: AegisClient) -> str:
    parts = [f"{client.first_name} {client.last_name}"]
    if client.address:
        parts.append(client.address)
    city_state_zip = ", ".join(filter(None, [client.city, client.state]))
    if client.zip_code:
        city_state_zip += f" {client.zip_code}"
    if city_state_zip.strip(", "):
        parts.append(city_state_zip.strip(", "))
    return "\n".join(parts)


def _state_ag(state: str) -> str:
    return _STATE_AG.get(state.upper(), "State Attorney General")


def _sol_lines(state: str) -> list:
    sol = _STATE_SOL.get(state.upper())
    if not sol:
        return []
    period, citation = sol
    return [
        f"Under {citation}, the statute of limitations on many consumer debts",
        f"in {state} is {period}. Reporting time-barred debt as currently due or",
        f"re-aging it violates FDCPA §807(2)(A) (false representation of legal status),",
        f"FCRA §623(a)(5) (re-aging prohibition), and 15 U.S.C. §1681c(a)(4)-(5).",
    ]


def _udap_line(state: str) -> str:
    udap = _STATE_UDAP.get(state.upper())
    if not udap:
        return ""
    name, cite = udap
    return f"Deceptive or misleading credit reporting also violates the {name}, {cite}."


def _breach_block() -> list:
    return [
        "Given recent data breaches and documented CRA enforcement failures, I have",
        "heightened concern that your verification systems cannot ensure accuracy:",
        "",
        "Enforcement actions confirming systemic noncompliance:",
        "  • CFPB v. Equifax (2025) — $15M penalty for improper dispute handling",
        "  • CFPB v. Experian (2025) — alleged sham investigations",
        "  • FTC/CFPB v. TransUnion (2023) — $15M settlement for accuracy failures",
        "  • TransUnion (2025) — $2.5M settlement for retaining deleted consumer data",
        "",
        "Data breaches affecting consumer PII:",
        "  • Equifax 2017 (147M consumers — SSNs, DOBs, addresses exposed)",
        "  • TransUnion July 2025 (4.4M consumers — SSNs, DOBs, emails, phone numbers)",
        "  • AT&T 2024 data incident (consumer is a confirmed class member)",
        "",
        "Because my SSN, date of birth, name, and address have been exposed in these",
        "incidents, reliance on third-party data brokers (LexisNexis, SageStream,",
        "Innovis, ARS, CoreLogic) is not authorized and does not satisfy your FCRA",
        "reinvestigation duty. Under GLBA §§6801-6802, you must protect nonpublic",
        "personal information. Verification must rely only on original-creditor",
        "documentation and a verified chain of title.",
    ]


# ---------------------------------------------------------------------------
# BUREAU DISPUTE LETTER
# Matches Cruel & Associates format: numbered 1)–6), blank date, CMRRR header
# ---------------------------------------------------------------------------

def _make_bureau_dispute_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or "bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         f"{bureau_name}\n[Bureau Address]")
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"
    state = (client.state or "").upper()
    ag = _state_ag(state)

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        recipient_addr,
        "",
        "RE: FORMAL DISPUTE – PERSONAL INFORMATION CORRECTION, REINVESTIGATION DEMAND,",
        "    METHOD OF VERIFICATION, AND FULL CONSUMER FILE DISCLOSURE",
        f"Consumer: {full_name}",
    ]
    if client.address:
        addr_line = client.address
        if client.city or client.state:
            addr_line += f", {client.city or ''}, {client.state or ''}"
        if client.zip_code:
            addr_line += f" {client.zip_code}"
        lines.append(f"Address: {addr_line}")
    lines += [
        "",
        f"To {bureau_name}:",
        "",
        f"This letter is a formal dispute of inaccurate, incomplete, obsolete,",
        f"inconsistent, and/or unverifiable information in my {bureau_name} consumer",
        f"report, pursuant to the FCRA (15 U.S.C. §§607(b), 611, 609, 623) and",
        f"applicable state law.",
        "",
        "1) PERSONAL INFORMATION CORRECTION",
        f"Correct my file to reflect ONLY:",
        f"  • Legal Name: {full_name}",
    ]
    if client.address:
        lines.append(f"  • Current Address: {client.address}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip())
    lines += [
        "  • Employer: NONE AUTHORIZED",
        "",
        "Delete all other names, addresses, phone numbers, and employer entries that",
        "are not accurate and verifiable. Inaccurate personal identifiers violate:",
        "  • FCRA §607(b) (maximum possible accuracy)",
        "  • FCRA §611(a) (duty to reinvestigate)",
        "  • CFPB accuracy guidance and FTC file-matching standards",
        "",
        "Any tradeline associated with inaccurate identifiers must also be deleted.",
        "",
        "2) DISPUTED NEGATIVE INFORMATION (ALL DEROGATORY ITEMS)",
        "I dispute all negative accounts, collections, charge-offs, and sold/assigned",
        "tradelines that are inaccurate, incomplete, inconsistent, obsolete, or",
        "unverifiable. This includes any tradeline that fails Metro 2 compliance",
        "requirements, lacks accurate DOFD reporting, or lacks proof of legal",
        "responsibility/ownership.",
        "",
    ]

    if round_.items:
        for i, item in enumerate(round_.items, 1):
            acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
            lines += [
                f"  ITEM {i}: {item.creditor_name.upper()}",
                f"  Account: {acct}",
                f"  Dispute: {item.dispute_reason}",
                f"  Basis: {item.fcra_basis or 'FCRA §§611, 623(a)(5); Metro 2 CRRG'}",
                f"  Violations: Inconsistent DOFD, improper status coding, balance",
                f"  discrepancy, and/or missing required Metro 2 fields.",
                "",
            ]
    else:
        lines += [
            "  All derogatory tradelines in my file are hereby disputed.",
            "  Specific account details are reflected in the attached affidavit.",
            "",
        ]

    # Metro 2 violations block
    lines += [
        "Metro 2 non-compliance grounds for deletion (any one sufficient):",
        "  • Conflicting Account Status Codes",
        "  • Inconsistent Date of First Delinquency (DOFD)",
        "  • Mixed open/charged-off status indicators",
        "  • Duplicate collection reporting of the same obligation",
        "  • Incorrect Portfolio Type, Compliance Codes, or Consumer Information Indicators",
        "  • Time-barred debts reported as currently active",
        "  • Misreported balances or past-due amounts",
        "",
    ]

    # Section 3: State SOL
    sol = _STATE_SOL.get(state)
    if sol:
        period, citation = sol
        lines += [
            f"3) {state} STATUTE OF LIMITATIONS NOTICE",
        ] + _sol_lines(state) + [""]
        udap = _udap_line(state)
        if udap:
            lines += [udap, ""]
    else:
        lines += [
            "3) STATUTE OF LIMITATIONS NOTICE",
            "Any reporting that implies enforceability where a debt is time-barred or",
            "near time-barred must be investigated for accuracy and legal status.",
            "",
        ]

    # Section 4: MOV
    lines += [
        "4) METHOD OF VERIFICATION",
        "If you verify any disputed item, provide the Method of Verification pursuant",
        "to 15 U.S.C. §611(a)(6)(B)(iii), including:",
        "  • Full name, address, and contact of the person who verified",
        "  • Specific method used (not merely 'verified by data furnisher')",
        "  • Description of documents reviewed during verification",
        "  • Confirmation that verification was conducted by a human reviewer,",
        "    not solely by automated e-OSCAR data matching",
        "",
        "A 'rubber-stamp' or e-OSCAR electronic response without substantive review",
        "of underlying documents does not satisfy FCRA's reinvestigation requirement.",
        "Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997); Hinkle v.",
        "Midland Credit Mgmt., Inc., 827 F.3d 298 (4th Cir. 2016).",
        "",
    ]

    # Breach block in MOV section
    lines += _breach_block() + [""]

    # Section 5: Full file disclosure
    lines += [
        "5) FULL CONSUMER FILE DISCLOSURE",
        "Provide my FULL consumer file pursuant to 15 U.S.C. §§609-610, including:",
        "  • All Metro 2 data fields and furnisher/source codes",
        "  • All dispute logs and verification logs",
        "  • All archived, suppressed, or deleted account records",
        "  • All prior addresses and name variations in your system",
        "  • Complete hard and soft inquiry records with permissible purpose",
        "  • All internal codes, notations, and fraud alerts in my file",
        "",
        "6) REQUIRED ACTION",
        "Within 30 days of receipt (FCRA §611(a)(1)):",
        "  • Reinvestigate all disputed items using original-creditor documentation",
        "  • Delete all information that cannot be verified through competent evidence",
        "    (FCRA §611(a)(5)(A))",
        "  • Correct personal information to reflect ONLY the data listed in Item 1",
        "  • Provide written notice of investigation results",
        "  • Send a free updated copy of my consumer report if changes are made",
        "    (FCRA §611(a)(6)(A))",
        "  • Notify all furnishers of any corrections or deletions",
        "    (FCRA §611(a)(6)(B)(i))",
        "  • Confirm whether my PII was included in any breach affecting your systems",
        "",
        f"Failure to comply will result in formal complaints to the CFPB, FTC, and the",
        f"{ag}, and may give rise to civil action under FCRA §§616-617.",
        "",
        "Enclosures:",
        f"  • Sworn Affidavit of {full_name}",
        "  • Proof of identity and proof of address (to be attached)",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AFFIDAVIT
# 12-statement sworn testimony under 28 U.S.C. §1746 + state evidence rule
# ---------------------------------------------------------------------------

def _make_affidavit(client: AegisClient, case: AegisCase, today: str) -> str:
    state = (client.state or "YOUR STATE").upper()
    county = client.city or "YOUR COUNTY"
    full_name = f"{client.first_name} {client.last_name}"
    sol = _STATE_SOL.get(state)
    sol_text = ""
    if sol:
        period, citation = sol
        sol_text = (f"{state}'s statute of limitations for many consumer debts is "
                    f"{period} pursuant to {citation}")
    else:
        sol_text = "the applicable statute of limitations for consumer debts in this state"

    evidence_cite = _STATE_EVIDENCE.get(state, "applicable state rules of evidence")
    udap = _STATE_UDAP.get(state)
    udap_cite = f"{udap[0]}, {udap[1]}" if udap else "applicable state consumer protection law"

    lines = [
        f"AFFIDAVIT OF {full_name.upper()}",
        "",
        f"STATE OF {state}",
        f"COUNTY OF {county.upper()}",
        "",
        f"I, {full_name}, residing at {client.address or '[Address]'}, "
        f"{client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip() + ",",
        "being duly sworn, state under penalty of perjury pursuant to 28 U.S.C. §1746",
        f"and {evidence_cite}:",
        "",
        "This affidavit constitutes sworn testimony admissible as evidence under the",
        "Federal Rules of Evidence and applicable state law. Any response from a credit",
        "reporting agency or data furnisher that contradicts the sworn statements herein",
        "may expose the responding party to civil and criminal liability. This document",
        "is intended to force escalation beyond automated e-OSCAR processing to CRA",
        "compliance departments, legal teams, and FCRA specialist investigators.",
        "",
        f"1. My legal name is {full_name}.",
        "",
        f"2. My only current and correct address is {client.address or '[Address]'}, "
        f"{client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip() + ".",
        "",
        "3. I have reviewed my consumer credit reports maintained by Experian, Equifax,",
        "   and TransUnion.",
        "",
        "4. My reports contain inaccurate, obsolete, incomplete, inconsistent, and/or",
        "   unverifiable information, including personal identifiers and tradeline data.",
        "   I have not authorized the reporting of any alternate names, prior addresses,",
        "   or employer information beyond what is stated herein.",
        "",
        "5. Certain tradelines lack accurate Date of First Delinquency (DOFD), contain",
        "   improper account status coding, contain inconsistent balances, or fail to",
        "   meet Metro 2 Credit Reporting Resource Guide (CRRG) standards. Material",
        "   inconsistencies across bureaus constitute inaccuracy under FCRA §607(b) and",
        "   §623(a)(1)(A), as courts have consistently held.",
        "",
        "6. Several collection and debt buyer accounts are reported without proof of",
        "   ownership, assignment, or chain of title, rendering them unverifiable under",
        "   FCRA §§609, 611, and 623.",
        "",
        f"7. Certain accounts appear to be time-barred or near time-barred. {sol_text}.",
        "   Debts must not be misrepresented as legally enforceable.",
        "",
        "8. Reporting time-barred or legally unenforceable debt without disclosure",
        "   constitutes a misrepresentation of legal status under FDCPA §807(2)(A)",
        "   and a re-aging violation under FCRA §623(a)(5) and 15 U.S.C. §1681c(a)(4)-(5).",
        f"   Deceptive reporting also violates the {udap_cite}.",
        "",
        "9. I do not consent to verification through third-party data brokers, data",
        "   aggregators, or non-original-source databases, including but not limited to",
        "   LexisNexis, SageStream, CoreLogic, ARS, Innovis, or similar systems.",
        "   Verification must be based on competent evidence from the original creditor",
        "   and/or a lawful chain of title proving ownership and authority to report.",
        "",
        "10. Any reinvestigation relying solely on automated systems, including e-OSCAR",
        "    workflows, without a reasonable, independent investigation does not satisfy",
        "    FCRA §611(a) reinvestigation duties. Cushman v. Trans Union Corp., 115 F.3d",
        "    220 (3d Cir. 1997) (CRA must do more than parrot the furnisher). Hinkle v.",
        "    Midland Credit Mgmt., Inc., 827 F.3d 298 (4th Cir. 2016).",
        "",
        "11. The presence of conflicting data across bureaus for the same accounts",
        "    demonstrates the absence of a single, reliable, verifiable record, and",
        "    constitutes a concrete, particularized injury. TransUnion LLC v. Ramirez,",
        "    141 S. Ct. 2190 (2021).",
        "",
        "12. Recent data breaches materially increase the risk of mixed files, inaccurate",
        "    identity association, and reliance on compromised third-party databases:",
        "      • Equifax 2017 breach (147M consumers — SSNs, DOBs, addresses exposed)",
        "      • TransUnion July 2025 breach (4.4M consumers — SSNs, DOBs, emails exposed)",
        "      • AT&T 2024 data incident (I am a confirmed class member)",
        "    Under GLBA §§6801-6802, CRAs must protect nonpublic personal information.",
        "    These breaches demonstrate a pattern of inadequate data stewardship that",
        "    undermines the claimed reliability of any 'verified as accurate' statement.",
        "",
        "    Enforcement actions further confirm systemic noncompliance:",
        "      • CFPB v. Equifax (2025) — $15M penalty for improper dispute handling",
        "      • CFPB v. Experian (2025) — alleged sham investigations",
        "      • FTC/CFPB v. TransUnion (2023) — $15M settlement for accuracy failures",
        "      • TransUnion (2025) — $2.5M settlement for retaining deleted data",
        "",
        "13. I request deletion of any information that cannot be verified as accurate,",
        "    complete, and timely under the FCRA and Metro 2 standards. Unverifiable",
        "    data must be deleted pursuant to FCRA §611(a)(5)(A).",
        "",
        "I affirm that the statements herein are true and correct to the best of my",
        "knowledge, information, and belief.",
        "",
        "Executed on this ___ day of __________, 2025.",
        "",
        "",
        f"{'_' * 36}",
        full_name,
        "",
        "",
        f"Subscribed and sworn before me this ___ day of __________, 2025.",
        "",
        "",
        f"{'_' * 36}",
        f"Notary Public for the State of {state.capitalize()}",
        "My Commission Expires: ______________",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# AUTHORIZATION / LIMITED POWER OF ATTORNEY
# ---------------------------------------------------------------------------

def _make_authorization_letter(client: AegisClient, today: str) -> str:
    full_name = f"{client.first_name} {client.last_name}"
    state = (client.state or "YOUR STATE").upper()
    client_addr = _client_addr_block(client)
    sol = _STATE_SOL.get(state)

    state_laws = "FCRA §§602, 607(b), 611, 623"
    if state == "SC":
        state_laws += "; South Carolina Unfair Trade Practices Act, S.C. Code §39-5-20"
    elif state == "MD":
        state_laws += ("; Maryland Commercial Law §14-1202; Maryland Consumer Protection Act"
                       " §13-301; Maryland Consumer Debt Collection Act §14-202")
    elif state == "MI":
        state_laws += "; Michigan Consumer Protection Act, Mich. Comp. Laws §445.903"

    lines = [
        "AUTHORIZATION LETTER",
        "",
        client_addr,
        "",
        "To: Equifax Information Services LLC",
        "    Experian Information Solutions, Inc.",
        "    TransUnion LLC",
        "",
        "From: Cruel and Associates",
        "      49 Foxhall Rd",
        "      Greenville, SC 29605",
        "      Email: cruelandassociates1@gmail.com",
        "      Phone: (864) 431-0400",
        "",
        "Date: ____________________",
        "",
        "NOTICE OF AUTHORIZATION AND REPRESENTATION",
        "",
        f"I, {full_name}, hereby authorize Cruel and Associates, located at",
        "49 Foxhall Rd, Greenville, SC 29605, to act as my authorized representative",
        "regarding all matters related to my consumer credit reporting, including",
        "but not limited to:",
        "",
        "1. Submitting disputes and reinvestigation requests under the Fair Credit",
        "   Reporting Act (FCRA).",
        "2. Requesting and receiving my credit reports and full consumer file disclosures.",
        "3. Requesting the Method of Verification for any disputed item reported on",
        "   my credit file.",
        "4. Communicating in writing with any credit reporting agency or their",
        "   authorized agents.",
        "5. Requesting deletion, correction, or reinvestigation of any item on my",
        "   credit report.",
        "6. Receiving copies of all written correspondence, notices, and reinvestigation",
        "   outcomes.",
        "",
        "I request that all responses, results, and documents related to any",
        "reinvestigation be sent to:",
        "",
        "    Cruel and Associates",
        "    49 Foxhall Rd",
        "    Greenville, SC 29605",
        "",
        "And a duplicate copy mailed to me at my home address:",
        "",
        f"    {full_name}",
        f"    {client.address or '[Address]'}",
    ]
    if client.city or client.state:
        lines.append(f"    {client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip())
    lines += [
        "",
        "This authorization is granted pursuant to federal and state law, including",
        f"but not limited to: {state_laws}.",
        "",
        "This authorization remains in effect until revoked in writing.",
        "",
        "CONSUMER SIGNATURE",
        "I affirm that I have read and understand the contents of this document.",
        "",
        f"Signature: {'_' * 42}",
        f"Printed Name: {full_name}",
        f"Date: {'_' * 47}",
        "",
        "NOTARY ACKNOWLEDGMENT",
        "",
        f"State of {'_' * 28}",
        f"County of {'_' * 27}",
        "",
        f"Subscribed and sworn before me on this ______ day of ______________, 20____,",
        f"by {full_name}, who is personally known to me or who has produced",
        "valid identification.",
        "",
        f"Notary Public Signature: {'_' * 33}",
        f"Printed Name: {'_' * 44}",
        f"Commission Number: {'_' * 39}",
        f"My Commission Expires: {'_' * 35}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DEBT COLLECTOR LETTER
# Items 3/4/5 format matching Cruel & Associates playbook
# ---------------------------------------------------------------------------

def _make_debt_collector_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_name = round_.recipient_name or "[Debt Collector Name]"
    recipient_addr_block = recipient_name
    if round_.recipient_address:
        recipient_addr_block += "\n" + round_.recipient_address
    else:
        recipient_addr_block += "\n[Address]"
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"
    state = (client.state or "").upper()
    ag = _state_ag(state)

    acct_nums = ", ".join(
        f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
        for item in round_.items
    ) if round_.items else "[As Reported]"

    lines = [
        client_addr,
        "",
        "Date: _____________",
        "",
        "Via Certified Mail – Return Receipt Requested",
        "",
        f"To: {recipient_addr_block}",
        "",
        f"RE: FORMAL DISPUTE, DEMAND FOR VALIDATION, AND CEASE COMMUNICATION",
        f"Account No(s): {acct_nums}",
        "",
        "To Whom It May Concern:",
        "",
        f"I dispute the above-referenced account(s) in their entirety. This letter",
        "serves as:",
        "(1) a written dispute and demand for validation under 15 U.S.C. §1692g,",
        "(2) a notice to CEASE COMMUNICATION under 15 U.S.C. §1692c(c), and",
        "(3) notice that continued credit reporting constitutes prohibited communication.",
        "",
        "ITEM 3 — CEASE COMMUNICATION",
        "Pursuant to 15 U.S.C. §1692c(c), you are hereby notified to cease all further",
        "communication with me regarding the alleged debt(s).",
        "",
        "ITEM 4 — VALIDATION / DIRECT DISPUTE",
        "Before any further action, provide competent evidence of:",
        "  • The original creditor and a complete itemization of the debt;",
        "  • A copy of the original contract or instrument bearing my signature;",
        "  • The full chain of title/assignment establishing your authority to collect;",
        "  • The accurate Date of First Delinquency (DOFD) as reported to each CRA;",
        "  • Proof your agency is licensed to collect in this state;",
        "  • Proof the amount claimed is accurate and legally owed.",
        "",
    ]

    if round_.items:
        lines.append("Accounts subject to this validation demand:")
        for i, item in enumerate(round_.items, 1):
            acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
            lines += [
                f"  {i}. {item.creditor_name.upper()} — Account {acct}",
                f"     Dispute: {item.dispute_reason}",
                f"     Basis: {item.fcra_basis or 'FDCPA §1692g; FCRA §§611, 623'}",
            ]
        lines.append("")

    lines += [
        "ITEM 5 — CREDIT REPORTING IS COMMUNICATION",
        "\"Communication\" includes conveying information regarding a debt through any",
        "medium (15 U.S.C. §1692a(2)). Reporting or continuing to report this account",
        "to any consumer reporting agency constitutes communication. Because I have",
        "invoked §1692c(c), you must cease credit reporting and request deletion of",
        "your tradeline(s). Continued reporting after this notice constitutes a",
        "false or misleading representation under FDCPA §1692e and an unfair practice",
        "under FDCPA §1692f. See Edeh v. Midland Credit Mgmt., Inc., 748 F.Supp.2d",
        "1030 (D. Minn. 2010).",
        "",
        "ADDITIONAL DIRECT DISPUTES",
        "  • Any reporting must comply with FCRA §§607(b), 611, and 623 and Metro 2",
        "    Credit Reporting Resource Guide standards.",
        "  • Do not rely on automated systems or third-party data brokers (e.g.,",
        "    LexisNexis, SageStream, Innovis, ARS). Such reliance is not authorized.",
    ]

    sol_lines = _sol_lines(state)
    if sol_lines:
        lines += ["  • " + sol_lines[0]] + ["    " + l for l in sol_lines[1:]]

    udap = _udap_line(state)
    if udap:
        lines += ["  • " + udap]

    lines += [
        "  • If you contend reporting may continue for any limited purpose, provide",
        "    your legal basis in writing.",
        "",
        "REMEDIAL ACTION REQUIRED",
        "Cease all communication, terminate collection efforts, and request deletion",
        "of any tradeline(s) you furnished. Provide written confirmation of compliance",
        "within 30 days.",
        "",
        f"Failure to comply will result in complaints to the CFPB, FTC, and the",
        f"{ag}, and may give rise to civil liability under FDCPA §1692k and FCRA §§616-617.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# STANDALONE PERSONAL INFORMATION DISPUTE
# ---------------------------------------------------------------------------

def _make_personal_info_dispute(client: AegisClient, bureau: str, today: str) -> str:
    full_name = f"{client.first_name} {client.last_name}"
    client_addr = _client_addr_block(client)
    bureau_name = bureau.capitalize() if bureau else "[Bureau]"
    recipient_addr = _BUREAU_ADDRESS.get(bureau.lower() if bureau else "", f"{bureau_name}\n[Bureau Address]")

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        recipient_addr,
        "",
        "RE: PERSONAL INFORMATION DISPUTE AND CORRECTION DEMAND",
        "",
        f"To {bureau_name}:",
        "",
        f"Correct my consumer file to reflect ONLY the following:",
        "",
        f"  Legal Name:      {full_name}",
    ]
    if client.address:
        lines += [
            f"  Current Address: {client.address}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip(),
        ]
    lines += [
        "  Employer:        NONE AUTHORIZED",
        "",
        "Delete all alternate names, former addresses, employer data, and any",
        "identifiers not expressly verified by documentary evidence.",
        "",
        "Failure to correct inaccurate personal identifiers violates:",
        "  • FCRA §607(b) — maximum possible accuracy",
        "  • FCRA §611(a) — duty to reinvestigate upon notice of dispute",
        "  • CFPB accuracy guidance",
        "  • FTC file-matching standards",
        "",
        "Any tradeline associated with inaccurate identifiers must also be deleted.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CEASE & DESIST LETTER
# ---------------------------------------------------------------------------

def _make_cease_desist_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_name = round_.recipient_name or "[Debt Collector]"
    recipient_addr_block = recipient_name + ("\n" + round_.recipient_address if round_.recipient_address else "")
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        client_addr,
        "",
        "Date: _____________",
        "",
        "Via Certified Mail – Return Receipt Requested",
        "",
        recipient_addr_block,
        "",
        "RE: FORMAL CEASE AND DESIST — All Collection Communication",
        "    Pursuant to FDCPA §1692c(c) | 15 U.S.C. §1692c(c)",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {full_name}, hereby formally and unequivocally demand that you",
        "IMMEDIATELY CEASE ALL COMMUNICATION with me regarding any and all alleged",
        "debts, pursuant to FDCPA §1692c(c), 15 U.S.C. §1692c(c).",
        "",
        "This demand applies to ALL communication including:",
        "  • Telephone calls to any number associated with me",
        "  • Written correspondence to any address",
        "  • Email or electronic communication of any kind",
        "  • Text messages or digital contact",
        "  • Contact through third parties",
        "  • Any credit reporting updates regarding the alleged debt",
        "",
        "Under FDCPA §1692c(c), upon receipt of this notice you may ONLY contact me to:",
        "  1. Advise that further collection efforts are being terminated",
        "  2. Notify me of a specific remedy you intend to invoke",
        "",
        "CREDIT REPORTING IS COMMUNICATION:",
        "Continued reporting of any alleged debt to consumer reporting agencies after",
        "receipt of this cease notice constitutes continued collection communication",
        "under FDCPA §1692a(2). Any such reporting will be treated as a willful FDCPA",
        "violation subject to civil action under FDCPA §1692k.",
        "",
        "ACCOUNTS SUBJECT TO THIS DEMAND:",
    ]
    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
        lines.append(f"  {i}. {item.creditor_name} — Account {acct}")
    lines += [
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# METHOD OF VERIFICATION LETTER
# ---------------------------------------------------------------------------

def _make_method_of_verification_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Credit Bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         round_.recipient_name or bureau_name)
    if round_.recipient_address and round_.bureau not in _BUREAU_ADDRESS:
        recipient_addr += "\n" + round_.recipient_address
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        recipient_addr,
        "",
        "RE: Method of Verification (MOV) Demand",
        "    Pursuant to FCRA §611(a)(6)(B)(iii) | 15 U.S.C. §1681i(a)(6)(B)(iii)",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {full_name}, received your response to my prior credit dispute",
        "indicating that the disputed information was 'verified.' I am NOT satisfied",
        "with this response and hereby demand a complete Method of Verification (MOV)",
        "pursuant to FCRA §611(a)(6)(B)(iii).",
        "",
        "A statement that information was 'verified by the data furnisher' through",
        "an automated e-OSCAR system does NOT satisfy the FCRA's reinvestigation",
        "requirement. Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997);",
        "Hinkle v. Midland Credit Mgmt., Inc., 827 F.3d 298 (4th Cir. 2016).",
        "",
        "FOR EACH DISPUTED ITEM, PROVIDE:",
        "",
        "  1. VERIFIER IDENTITY:",
        "     — Full legal name and contact of the person who conducted verification",
        "     — Whether verification was performed by a human or automated system",
        "",
        "  2. VERIFICATION METHOD:",
        "     — Specific method used (NOT 'e-OSCAR' or 'data furnisher confirmed')",
        "     — Identification of every document reviewed",
        "",
        "  3. DOCUMENTS REVIEWED:",
        "     — Copies of any documents relied upon to verify the information",
        "     — Who provided those documents",
        "",
        "  4. TIMELINE:",
        "     — Date dispute was transmitted to the furnisher",
        "     — Date furnisher responded",
        "     — Date final determination was made",
        "",
        "Items for which MOV is demanded:",
    ]
    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
        lines += [
            f"  {i}. {item.creditor_name} — Account {acct}",
            f"     Original Dispute: {item.dispute_reason}",
        ]
    lines += [
        "",
        "Under TransUnion LLC v. Ramirez, 141 S. Ct. 2190 (2021), unverifiable",
        "credit report information causes concrete, particularized injury. If you",
        "cannot provide the above information, the disputed data must be deleted",
        "(FCRA §611(a)(5)(A)).",
        "",
        "You have 15 days from receipt of this demand to provide the requested",
        "information.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FULL FILE DISCLOSURE LETTER
# ---------------------------------------------------------------------------

def _make_full_file_disclosure_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Credit Bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         round_.recipient_name or bureau_name)
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        recipient_addr,
        "",
        "RE: Full Consumer File Disclosure Demand",
        "    Pursuant to FCRA §§609, 610 | 15 U.S.C. §§1681g, 1681h",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {full_name}, formally demand complete disclosure of all information",
        "in my consumer file pursuant to FCRA §609 and §610.",
        "",
        "COMPLETE DISCLOSURE DEMANDED:",
        "",
        "  1. ALL TRADELINE DATA — every account, including archived/suppressed records;",
        "     complete Metro 2 fields; all subscriber/furnisher codes and contacts",
        "",
        "  2. ALL INQUIRY DATA — hard and soft inquiries with permissible purpose for each",
        "",
        "  3. ALL PERSONAL INFORMATION — every name variation, address, employer,",
        "     phone number, and SSN variation maintained in my file",
        "",
        "  4. DISPUTE HISTORY — all prior disputes, outcomes, notices transmitted",
        "     to furnishers, and furnisher responses received",
        "",
        "  5. INTERNAL DATA — all internal codes, scores, notations, source codes,",
        "     fraud alerts, and security freezes in my file",
        "",
        "  6. ARCHIVED DATA — all previously deleted or archived information; any",
        "     information from files that were merged with mine; any mixed-file",
        "     indicators or corrections made",
        "",
        "Please provide this disclosure in writing within 15 days.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# FAILURE TO INVESTIGATE / ROUND 2 ESCALATION LETTER
# ---------------------------------------------------------------------------

def _make_failure_to_investigate_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Bureau/Furnisher").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         round_.recipient_name or bureau_name)
    if round_.recipient_address and round_.bureau not in _BUREAU_ADDRESS:
        recipient_addr += "\n" + round_.recipient_address
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"
    state = (client.state or "").upper()
    ag = _state_ag(state)

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        recipient_addr,
        "",
        "RE: Failure to Conduct Reasonable Investigation — Formal Notice",
        "    Pursuant to FCRA §§611, 616, 617 | 15 U.S.C. §§1681i, 1681n, 1681o",
        "",
        "To Whom It May Concern:",
        "",
        f"On [insert date of prior dispute], I disputed inaccurate and inconsistent",
        "information on my credit report, including but not limited to the following:",
        "",
    ]

    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
        lines += [
            f"  {i}. {item.creditor_name.upper()} — Account {acct}",
            f"     Dispute: {item.dispute_reason}",
            f"     Status: UNRESOLVED",
            "",
        ]

    lines += [
        "Your agency either:",
        "  • Failed to respond within the statutory 30-day time limit, OR",
        "  • Returned a boilerplate 'verified as accurate' response without providing",
        "    any method of verification or documentation.",
        "",
        "VIOLATIONS OF LAW",
        "",
        "This constitutes a violation of your obligations under:",
        "  • FCRA §611(a), 15 U.S.C. §1681i — duty to conduct a reasonable reinvestigation",
        "  • FCRA §607(b), 15 U.S.C. §1681e(b) — duty to ensure maximum possible accuracy",
        "  • FCRA §611(a)(6)(B)(iii) — duty to provide the method of verification",
        "",
        "Because you have failed to properly investigate, you must immediately delete",
        "these disputed items from my credit report.",
        "",
        "SUBSTANTIVE INVESTIGATION FAILURE",
        "",
        "Your generic 'verified as accurate' responses without supporting documentation",
        "demonstrate non-compliance. Federal regulators have confirmed similar behavior",
        "is unlawful:",
        "  • CFPB v. Equifax (2025) — $15M penalty for improper dispute handling",
        "  • CFPB v. Experian (2025) — alleged 'sham' dispute reviews",
        "  • FTC/CFPB v. TransUnion (2023) — $15M settlement for accuracy failures",
        "  • TransUnion (2025) — $2.5M for retaining deleted consumer data",
        "",
        "You must perform a new, independent investigation with the original creditor",
        "and provide documented results.",
        "",
        "DATA BREACH AND VERIFICATION RELIABILITY",
        "",
    ] + _breach_block() + [
        "",
        "REQUIRED ACTION",
        "  1. Delete the disputed tradelines immediately if proper original-creditor",
        "     verification cannot be produced.",
        "  2. Provide a full written explanation of your reinvestigation procedures.",
        "  3. Confirm whether my PII was impacted by any recent or past breaches.",
        "",
        f"Failure to comply within 15 days of receipt will result in formal complaints",
        f"to the CFPB, FTC, and the {ag}, along with consideration of civil remedies",
        f"under FCRA §§616-617. Willful noncompliance subjects you to statutory damages",
        f"of $100–$1,000 per violation, punitive damages, and attorney's fees.",
        f"Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007).",
        "",
        "PLEASE GOVERN YOURSELF ACCORDINGLY.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# STUDENT LOAN VALIDATION LETTER (DOE/DMCS variant)
# ---------------------------------------------------------------------------

def _make_student_loan_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_name = round_.recipient_name or "Debt Management and Collections System (DMCS)"
    recipient_addr_block = recipient_name
    if round_.recipient_address:
        recipient_addr_block += "\n" + round_.recipient_address
    else:
        recipient_addr_block += "\nU.S. Department of Education\nP.O. Box 5609\nGreenville, TX 75403-5609"
    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        client_addr,
        "",
        "Date: ____________________",
        "",
        "Via Certified Mail – Return Receipt Requested",
        "",
        recipient_addr_block,
        "",
        "RE: Dispute of Student Loan Debt and Validation Request",
        "    Pursuant to FDCPA 15 U.S.C. §1692g; FCRA 15 U.S.C. §§1681i, 1681s-2",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {full_name}, formally dispute the student loan debt(s) associated with",
        "my name and request validation pursuant to the Fair Debt Collection Practices",
        "Act (FDCPA), 15 U.S.C. §1692g, and the Fair Credit Reporting Act (FCRA),",
        "15 U.S.C. §§1681i and 1681s-2.",
        "",
        "If you are currently reporting this debt to any credit bureau, you are",
        "required to:",
        "  • Mark the debt as 'disputed' during investigation",
        "  • Cease collection until verification is provided",
        "  • Comply with Metro 2 standards for accuracy and integrity",
        "",
        "VALIDATION REQUIRED:",
        "",
        "1. The original signed promissory note or loan agreement bearing my signature",
        "2. The chain of title if the debt was transferred or assigned",
        "3. A full payment ledger with interest accrual and disbursement details",
        "4. Proof of Department of Education authorization to collect",
        "5. The legal authority for continued reporting to credit bureaus",
        "",
    ]

    if round_.items:
        lines.append("Accounts subject to this validation demand:")
        for i, item in enumerate(round_.items, 1):
            acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
            lines += [
                f"  {i}. {item.creditor_name} — Account {acct}",
                f"     Dispute: {item.dispute_reason}",
            ]
        lines.append("")

    lines += [
        "NOTE: The FDCPA applies to private collectors and collection agencies acting",
        "on federal student loans. Where the Department of Education acts directly,",
        "FCRA §§611 and 623 and the Higher Education Act govern accuracy and",
        "reinvestigation obligations.",
        "",
        "If you cannot provide this documentation within 30 days, I request that you",
        "cease all collection activity and remove any related tradelines from all",
        "consumer reporting agencies.",
        "",
        "Failure to respond will be treated as a willful violation of federal law",
        "and reported to the CFPB and other applicable regulatory bodies.",
        "",
        "This request is not a refusal to pay, but a request for validation under",
        "federal law.",
        "",
        "Sincerely,",
        "",
        "",
        f"{'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CFPB COMPLAINT
# ---------------------------------------------------------------------------

def _make_cfpb_complaint(round_: DisputeRound, client: AegisClient, today: str) -> str:
    full_name = f"{client.first_name} {client.last_name}"
    client_addr = _client_addr_block(client)
    state = (client.state or "").upper()
    ag = _state_ag(state)
    sol = _STATE_SOL.get(state)
    sol_cite = f"{sol[0]} ({sol[1]})" if sol else "the applicable statute of limitations"

    lines = [
        "CFPB COMPLAINT",
        "Submit at: https://www.consumerfinance.gov/complaint/",
        "",
        "Complainant",
        client_addr,
        f"Email: [email]",
        f"Phone: [phone]",
        "",
        f"Date: {today}",
        "",
        "Companies Complained About:",
        "  Equifax Information Services LLC",
        "  Experian Information Solutions, Inc.",
        "  TransUnion LLC",
        "",
        "Product/Issue:",
        "Credit reporting → Incorrect information on credit report / Failure to",
        "investigate / Failure to provide method of verification / Failure to correct",
        "personal information",
        "",
        "Summary of the Problem:",
        "",
        f"I filed written disputes with each CRA identifying inaccurate and inconsistent",
        "tradelines and requesting correction of my personal identifying information (PII).",
        "The bureaus (1) failed to conduct a reasonable reinvestigation, (2) failed to",
        "provide the method of verification, and (3) failed to correct my PII.",
        f"My file must reflect only: Name: {full_name}",
    ]
    if client.address:
        lines += [
            f"Address: {client.address}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip(),
        ]
    lines += [
        "No phone number or employer on file.",
        "",
        "Recent data breaches (TransUnion 2025; Equifax 2017; AT&T 2024 — I am a",
        "confirmed class member) increase the risk of mixed files and make it",
        "unreasonable for CRAs to rely on third-party vendor databases instead of",
        "original-creditor documentation. Federal enforcement actions also demonstrate",
        "a pattern of CRA noncompliance:",
        "  • CFPB v. Equifax (2025) — $15M penalty for improper dispute handling",
        "  • CFPB v. Experian (2025) — alleged sham investigations",
        "  • FTC/CFPB v. TransUnion (2023) — $15M settlement for accuracy failures",
        "  • TransUnion (2025) — $2.5M for retaining deleted consumer data",
        "",
        "Timeline (summarized):",
        "  [Date] — Mailed disputes to each CRA listing inaccurate tradelines and",
        "            requesting PI corrections via Certified Mail.",
        "  [Date] — Received either no response, or generic 'verified as accurate'",
        "            results without documentation.",
        "  [Date] — Sent Method of Verification letters demanding furnisher identity,",
        "            procedures used, and copies of documents relied upon.",
        "  [Date] — Sent Failure to Investigate notices and again demanded PI correction.",
        "  To date, CRAs have not provided the required MOV, have not corrected PI,",
        "  and inaccurate entries remain.",
        "",
        "Examples of disputed issues (non-exhaustive):",
    ]

    if round_.items:
        for item in round_.items:
            lines.append(f"  • {item.creditor_name}: {item.dispute_reason}")
    else:
        lines += [
            "  • Inconsistent/dual status (reported both open and charged-off)",
            "  • Balance/DOFD mismatches across bureaus (Metro 2 fields 4-7)",
            "  • Duplicate collection reporting of the same obligation",
            "  • Old names/addresses/employer still listed despite correction requests",
        ]

    lines += [
        "",
        "Laws/Standards Violated:",
        "  • FCRA §611 (15 U.S.C. §1681i): failure to reinvestigate and provide MOV",
        "    (§1681i(a)(6)(B)(iii))",
        "  • FCRA §607(b) (15 U.S.C. §1681e(b)): failure to ensure maximum accuracy",
        "  • FCRA §609 (15 U.S.C. §1681g): failure to provide complete file disclosure",
        "  • Metro 2 CRRG: inconsistent account status, DOFD, balances; duplicate TLs",
        f"  • FDCPA §807(2)(A): misrepresentation of time-barred debt (SOL: {sol_cite})",
        "  • GLBA §§6801-6802: failure to protect nonpublic personal information",
    ]
    udap = _STATE_UDAP.get(state)
    if udap:
        lines.append(f"  • {udap[0]}, {udap[1]}: deceptive/misleading credit reporting")

    lines += [
        "",
        "Harm Suffered:",
        "Increased risk of mixed file/identity confusion due to data breaches; wasted",
        "time and expense; adverse credit decisions and reputational harm from",
        "inaccurate data.",
        "",
        "Resolution Requested:",
        "  1. Require each CRA to perform a new, independent reinvestigation and",
        "     provide the method of verification (furnisher's name/contact, procedures",
        "     used, and copies of documents relied upon).",
        f"  2. Correct my personal information to show only: Name: {full_name}",
    ]
    if client.address:
        lines += [
            f"     Address: {client.address}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".rstrip(),
        ]
    lines += [
        "     No phone number and no employer listed. Remove all other names/addresses.",
        "  3. Delete any tradeline that cannot be verified with original-creditor",
        "     documentation, and remove duplicate entries; correct all Metro 2 fields.",
        "  4. Provide a free updated credit report and notify all recipients of my",
        "     report within the last six months of corrections.",
        "  5. Confirm whether my PII was included in the TransUnion and/or Equifax",
        "     breaches and what mitigation was taken during reinvestigation.",
        "  6. Any additional relief the CFPB deems appropriate to ensure ongoing",
        "     FCRA compliance.",
        "",
        "Attachments Available Upon Request:",
        "  • Copies of disputes, MOV letters, and failure-to-investigate letters",
        "    (with certified mail receipts)",
        "  • Credit report excerpts showing inaccuracies and PI errors",
        "  • AT&T data-incident notice confirming class membership",
        "  • ID and proof of address",
        "",
        "Consent to share complaint with companies named: Yes.",
        "",
        f"Signature: {'_' * 36}",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DISPATCHER
# ---------------------------------------------------------------------------

def _make_dispute_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_type = (round_.recipient_type or "bureau").lower()

    if recipient_type == "bureau":
        return _make_bureau_dispute_letter(round_, client, today)
    if recipient_type in ("collection_agency", "debt_buyer", "debt_collector"):
        return _make_debt_collector_letter(round_, client, today)
    if recipient_type == "cease_desist":
        return _make_cease_desist_letter(round_, client, today)
    if recipient_type == "method_of_verification":
        return _make_method_of_verification_letter(round_, client, today)
    if recipient_type == "full_file_disclosure":
        return _make_full_file_disclosure_letter(round_, client, today)
    if recipient_type == "failure_to_investigate":
        return _make_failure_to_investigate_letter(round_, client, today)
    if recipient_type == "student_loan":
        return _make_student_loan_letter(round_, client, today)
    if recipient_type == "cfpb_complaint":
        return _make_cfpb_complaint(round_, client, today)
    if recipient_type == "personal_info_dispute":
        return _make_personal_info_dispute(client, round_.bureau or "", today)

    # Generic fallback for creditor/furnisher/regulatory types
    if recipient_type == "cfpb":
        recipient_addr = "Consumer Financial Protection Bureau\nP.O. Box 27170\nWashington, DC 20038"
        re_line = "RE: Formal Complaint — Failure to Correct Inaccurate Credit Information"
        authority = "    Pursuant to FCRA §§611, 623"
        body_intro = [
            "I am filing this formal complaint because a prior dispute submitted to the",
            "credit bureau and/or furnisher was ignored or resulted in an insufficient",
            "investigation. The inaccurate information described below continues to appear",
            "on my credit report in violation of FCRA §§611 and 623.",
        ]
        close_demands = [
            "I respectfully request that the CFPB:",
            "  1. Investigate the failure to comply with FCRA §§611 and 623",
            "  2. Direct all responsible parties to correct or delete inaccurate information",
            "  3. Take appropriate enforcement action",
            "  4. Note this complaint in the public Consumer Complaint Database",
        ]
    elif recipient_type == "ftc":
        recipient_addr = "Federal Trade Commission\nConsumer Response Center\n600 Pennsylvania Avenue NW\nWashington, DC 20580"
        re_line = "RE: FTC Complaint — FCRA/FDCPA Violations"
        authority = "    Pursuant to FTC Act §5 and FCRA"
        body_intro = [
            "I am submitting this complaint regarding unfair or deceptive acts and",
            "practices in connection with my consumer credit report.",
        ]
        close_demands = [
            "I request that the FTC:",
            "  1. Investigate the unfair and deceptive practices described above",
            "  2. Take enforcement action against the responsible parties",
            "  3. Require corrective action to remedy the harm caused",
        ]
    elif recipient_type == "state_ag":
        state = (client.state or "").upper()
        ag_name = _state_ag(state)
        recipient_addr = round_.recipient_address or f"{ag_name}\n[State Capital Address]"
        re_line = "RE: Consumer Protection Complaint — Credit Reporting Violations"
        authority = "    Pursuant to State UDAP Laws and FCRA"
        udap = _STATE_UDAP.get(state)
        udap_cite = f"{udap[0]}, {udap[1]}" if udap else "applicable state consumer protection law"
        body_intro = [
            "I am submitting this complaint regarding violations of state consumer",
            f"protection laws ({udap_cite}) and the federal Fair Credit Reporting Act",
            "committed by the parties identified below.",
        ]
        close_demands = [
            f"I respectfully request that the {ag_name}:",
            "  1. Investigate violations of state consumer protection laws and the FCRA",
            "  2. Take appropriate enforcement action",
            "  3. Require correction of all inaccurate information",
        ]
    elif recipient_type == "medical_provider":
        recipient_addr = (round_.recipient_name or "Medical Provider")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Medical Debt and HIPAA Privacy Concern"
        authority = "    Pursuant to FCRA §605(a)(6), HIPAA 45 CFR §164.502"
        body_intro = [
            "I formally dispute the medical debt below. Under FCRA §605(a)(6) and CFPB",
            "2022 medical debt rules, paid or settled medical debt and debt under $500",
            "is subject to special credit reporting restrictions. Sharing PHI with CRAs",
            "without written authorization may warrant complaint to HHS OCR.",
        ]
        close_demands = [
            "I demand that you:",
            "  1. Cease all collection activity on the disputed medical debt",
            "  2. Instruct all CRAs to delete this account",
            "  3. Provide documentation of any PHI authorization signed by me",
            "  4. Confirm deletion in writing within 30 days",
        ]
    elif recipient_type == "student_loan_servicer":
        recipient_addr = (round_.recipient_name or "Student Loan Servicer")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Student Loan Servicing Error and Inaccurate Reporting"
        authority = "    Pursuant to FCRA §623, Higher Education Act §455"
        body_intro = [
            "I formally dispute inaccurate student loan information you have reported",
            "to consumer reporting agencies. Under FCRA §623 and HEA §455, you must",
            "accurately report payment history, forbearance periods, and balances.",
        ]
        close_demands = [
            "I demand that you:",
            "  1. Investigate and correct all inaccurate information within 30 days",
            "  2. Report corrections to all CRAs (FCRA §623(b))",
            "  3. Provide written confirmation of all corrections",
        ]
    elif recipient_type == "auto_lender":
        recipient_addr = (round_.recipient_name or "Auto Lender")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Wrongful Repossession and Deficiency Balance"
        authority = "    Pursuant to UCC Article 9 §§609-614, FDCPA §809(b), FCRA §623"
        body_intro = [
            "I formally dispute the repossession and/or deficiency balance reported",
            "on my consumer credit report. Under UCC Article 9 §§609-614, a creditor",
            "must provide proper notice and conduct a commercially reasonable sale.",
            "Failure voids the deficiency balance claim.",
        ]
        close_demands = [
            "I demand proof of:",
            "  1. Proper pre-repossession notice (UCC Art. 9 and state law)",
            "  2. Commercially reasonable sale (UCC §9-610)",
            "  3. Complete deficiency balance accounting",
            "  4. Correction of all CRA reporting (FCRA §623)",
        ]
    elif recipient_type == "intent_to_sue":
        recipient_addr = (round_.recipient_name or "Respondent")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: NOTICE OF INTENT TO FILE CIVIL LAWSUIT — FCRA Violations"
        authority = "    Pursuant to FCRA §§616, 617 | Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007)"
        body_intro = [
            "NOTICE IS HEREBY GIVEN that I intend to file a civil lawsuit for violations",
            "of FCRA §§616, 617. Your conduct satisfies the willfulness standard of",
            "Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007) (reckless disregard = willfulness).",
        ]
        close_demands = [
            "DEMAND FOR CURE — 10 DAYS:",
            "  1. Correct all inaccurate information in your records",
            "  2. Notify all CRAs of required corrections",
            "  3. Provide written confirmation of all corrections",
            "",
            "Failure to cure within 10 days will result in civil action.",
            "PLEASE GOVERN YOURSELF ACCORDINGLY.",
        ]
    elif recipient_type == "pay_for_delete":
        recipient_addr = (round_.recipient_name or "Creditor/Collector")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Settlement Offer — Pay for Delete Agreement"
        authority = "    Pursuant to FCRA §623"
        body_intro = [
            "I propose the following settlement WITHOUT admission of debt validity.",
            "This offer is CONTINGENT upon complete deletion from ALL CRAs within",
            "30 days of payment. NO PAYMENT WILL BE MADE without a signed written",
            "agreement confirming delete-for-payment terms.",
        ]
        close_demands = [
            "Terms:",
            "  1. Upon signed written agreement, I will remit payment within [X] days",
            "  2. You will delete this account from ALL CRAs within 30 days of payment",
            "  3. You agree not to re-sell or transfer this debt",
            "  4. Payment is NOT admission of debt validity",
            "",
            "Respond in writing within 15 days.",
        ]
    else:
        recipient_addr = (round_.recipient_name or "Creditor")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = f"RE: Dispute of Inaccurate Account Information — Round {round_.round_number}"
        authority = "    Pursuant to FCRA §623"
        body_intro = [
            "I formally dispute inaccurate information you have reported to consumer",
            "reporting agencies. Under FCRA §623, furnishers must report accurate data",
            "and investigate disputes within 30 days.",
        ]
        close_demands = [
            "Please:",
            "  1. Correct any inaccurate information with all CRAs, OR",
            "  2. Delete the account if information cannot be verified",
            "",
            "Under FCRA §623(b), provide written confirmation of corrections.",
        ]

    client_addr = _client_addr_block(client)
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        client_addr, "", "Date: ____________________", "", recipient_addr, "",
        re_line, authority, "",
        "To Whom It May Concern:",
        "",
    ] + body_intro + [
        "",
        _SEP,
        "DISPUTED ACCOUNTS",
        _SEP,
    ]

    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "[As Reported]"
        lines += [
            "",
            f"Item {i}: {item.creditor_name}",
            f"  Account: {acct}",
            f"  Dispute Reason: {item.dispute_reason}",
            f"  Legal Basis: {item.fcra_basis or 'FCRA §623'}",
        ]

    lines += [
        "", _SEP, "",
    ] + close_demands + [
        "",
        "Sincerely,",
        "", "",
        full_name,
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CASE SUMMARY REPORT
# ---------------------------------------------------------------------------

def _make_text_report(case: AegisCase, client: AegisClient, findings: list, tradelines: list, strategy: list) -> str:
    lines = [
        "=" * 70,
        "AEGIS CREDIT INVESTIGATOR — CASE SUMMARY REPORT",
        "=" * 70,
        "",
        "COMPLIANCE NOTICE: This report is for investigator and client review only.",
        "No finding constitutes legal advice, a proven violation, or a guarantee",
        "of any outcome. All findings require human review before any action.",
        "",
        f"Case Number: {case.case_number}",
        f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Client: {client.first_name} {client.last_name}",
        f"Status: {case.status}",
        f"Goal: {case.goal or 'Not specified'}",
        "",
        _SEP,
        f"TRADELINE SUMMARY ({len(tradelines)} accounts)",
        _SEP,
    ]
    bureaus = {}
    for tl in tradelines:
        b = tl.bureau or "unknown"
        bureaus.setdefault(b, []).append(tl)
    for bureau, tls in bureaus.items():
        lines.append(f"\n{bureau.upper()}:")
        for tl in tls:
            flag = "[DEROGATORY] " if tl.derogatory else ""
            lines.append(f"  {flag}{tl.creditor_name} ({tl.account_type}) — Status: {tl.payment_status}"
                         f"{' — Balance: $' + str(tl.balance) if tl.balance else ''}")

    lines += ["", _SEP, f"FINDINGS ({len(findings)} total)", _SEP]
    for f in findings:
        lines.append(f"\n[{f.severity.upper()}] {f.title}")
        lines.append(f"  Type: {f.finding_type} | FCRA: {f.fcra_section or 'N/A'}")
        lines.append(f"  {f.description}")
        lines.append("  *** REQUIRES HUMAN REVIEW BEFORE ANY ACTION ***")

    lines += ["", _SEP, f"RECOMMENDED STRATEGY ({len(strategy)} items)", _SEP]
    for s in strategy:
        lines.append(f"\nP{s.priority} — {s.title} [{s.strategy_type}]")
        lines.append(f"  Timeline: {s.estimated_timeline or 'TBD'}")
        if s.description:
            lines.append(f"  {s.description}")
        try:
            actions = json.loads(s.action_items) if s.action_items else []
            for a in actions:
                lines.append(f"    • {a}")
        except Exception:
            pass

    lines += ["", "=" * 70, "END OF REPORT — Aegis Credit Investigator", "=" * 70]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# ROUTER ENDPOINTS
# ---------------------------------------------------------------------------

@router.post("/case/{case_id}/generate")
def generate_report(case_id: int, report_type: str = "summary", db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    findings = db.query(Finding).filter(Finding.case_id == case_id).all()
    tradelines = db.query(Tradeline).filter(Tradeline.case_id == case_id).all()
    strategy = db.query(StrategyItem).filter(StrategyItem.case_id == case_id).order_by(StrategyItem.priority).all()

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    filename = f"aegis_report_{case_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    file_path = os.path.join(settings.REPORTS_DIR, filename)

    content = _make_text_report(case, client, findings, tradelines, strategy)
    with open(file_path, "w") as f:
        f.write(content)

    record = GeneratedReport(case_id=case_id, report_type=report_type, file_path=file_path)
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "case_id": record.case_id,
        "report_type": record.report_type,
        "file_path": record.file_path,
        "generated_at": record.generated_at.isoformat() if record.generated_at else None,
    }


@router.get("/case/{case_id}")
def list_reports(case_id: int, db: Session = Depends(get_db)):
    reports = db.query(GeneratedReport).filter(GeneratedReport.case_id == case_id).all()
    return [{
        "id": r.id,
        "case_id": r.case_id,
        "report_type": r.report_type,
        "file_path": r.file_path,
        "generated_at": r.generated_at.isoformat() if r.generated_at else None,
    } for r in reports]


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(GeneratedReport).filter(GeneratedReport.id == report_id).first()
    if not r:
        raise HTTPException(404, "Report not found")
    if not os.path.exists(r.file_path):
        raise HTTPException(404, "Report file not found on disk")
    return FileResponse(r.file_path, filename=os.path.basename(r.file_path))


@router.get("/dispute-letter/{round_id}")
def download_dispute_letter(round_id: int, db: Session = Depends(get_db)):
    round_ = db.query(DisputeRound).filter(DisputeRound.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Dispute round not found")
    no_items_ok = (round_.recipient_type or "").lower() in (
        "full_file_disclosure", "cfpb_complaint", "personal_info_dispute",
    )
    if not round_.items and not no_items_ok:
        raise HTTPException(400, "This round has no dispute items — add items before downloading the letter.")
    case = db.query(AegisCase).filter(AegisCase.id == round_.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    today = datetime.now().strftime("%B %d, %Y")
    content = _make_dispute_letter(round_, client, today)
    slug = round_.bureau or (round_.recipient_name or round_.recipient_type or "letter").replace(" ", "_").lower()
    filename = f"dispute_letter_{slug}_round{round_.round_number}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/affidavit/{case_id}")
def download_affidavit(case_id: int, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    today = datetime.now().strftime("%B %d, %Y")
    content = _make_affidavit(client, case, today)
    filename = f"affidavit_{client.last_name}_{client.first_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/authorization/{case_id}")
def download_authorization(case_id: int, db: Session = Depends(get_db)):
    case = db.query(AegisCase).filter(AegisCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    client = db.query(AegisClient).filter(AegisClient.id == case.client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")

    today = datetime.now().strftime("%B %d, %Y")
    content = _make_authorization_letter(client, today)
    filename = f"authorization_{client.last_name}_{client.first_name}_{datetime.now().strftime('%Y%m%d')}.txt"
    return PlainTextResponse(
        content,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
