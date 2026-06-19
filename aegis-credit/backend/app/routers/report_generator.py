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

# State statute of limitations reference table
_STATE_SOL = {
    "SC": ("3 years", "S.C. Code § 15-3-530"),
    "MD": ("3 years", "Md. Code, Cts. & Jud. Proc. § 5-101"),
    "NY": ("6 years", "N.Y. C.P.L.R. § 213"),
    "CA": ("4 years", "Cal. Civ. Proc. Code § 337"),
    "TX": ("4 years", "Tex. Civ. Prac. & Rem. Code § 16.004"),
    "FL": ("5 years", "Fla. Stat. § 95.11(2)"),
    "GA": ("6 years", "O.C.G.A. § 9-3-24"),
    "NC": ("3 years", "N.C. Gen. Stat. § 1-52"),
    "VA": ("5 years", "Va. Code § 8.01-246"),
    "PA": ("4 years", "42 Pa. C.S. § 5525"),
    "OH": ("6 years", "Ohio Rev. Code § 2305.07"),
    "MI": ("6 years", "Mich. Comp. Laws § 600.5807"),
    "IL": ("5 years", "735 ILCS 5/13-205"),
    "NJ": ("6 years", "N.J. Stat. § 2A:14-1"),
    "WA": ("6 years", "Wash. Rev. Code § 4.16.040"),
    "AZ": ("6 years", "Ariz. Rev. Stat. § 12-548"),
    "CO": ("6 years", "Colo. Rev. Stat. § 13-80-103.5"),
    "TN": ("6 years", "Tenn. Code § 28-3-109"),
    "AL": ("6 years", "Ala. Code § 6-2-34"),
    "MN": ("6 years", "Minn. Stat. § 541.05"),
}

_SEP = "─" * 70
_SEP2 = "═" * 70


def _client_addr_block(client: AegisClient) -> str:
    parts = [f"{client.first_name} {client.last_name}"]
    if client.address:
        parts.append(client.address)
    if client.city or client.state or client.zip_code:
        parts.append(f"{client.city or ''}, {client.state or ''} {client.zip_code or ''}".strip(", "))
    return "\n".join(parts)


def _state_sol_notice(state: str) -> list:
    if not state:
        return []
    sol = _STATE_SOL.get(state.upper())
    if not sol:
        return []
    period, citation = sol
    return [
        "",
        f"NOTE — STATE STATUTE OF LIMITATIONS ({state.upper()}):",
        f"Under {citation}, the statute of limitations on consumer debt in {state}",
        f"is {period}. Any time-barred debt may not be represented as legally enforceable",
        f"under FDCPA § 1692e. See also Edeh v. Midland Credit Management, Inc.,",
        f"748 F.Supp.2d 1030 (D. Minn. 2010) (credit reporting constitutes collection",
        f"activity under FDCPA § 1692a(2)).",
    ]


def _make_bureau_dispute_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    """
    Full 6-section Master Dispute Structure per Cruel & Associates playbook.

    Section 1 — Personal Information Correction (FCRA § 607(b))
    Section 2 — Tradeline Disputes (FCRA §§ 611, 623(a)(5), Metro 2)
    Section 3 — TransUnion v. Ramirez Notice (concrete injury standard)
    Section 4 — Method of Verification Demand (FCRA § 611(a)(6)(B)(iii))
    Section 5 — Full Consumer File Disclosure (FCRA §§ 609, 610)
    Section 6 — Required Action + State SOL notice
    """
    bureau_name = (round_.bureau or "bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(), f"{bureau_name}\n[Bureau Address]")
    client_addr = _client_addr_block(client)
    state = (client.state or "").upper()

    lines = [
        client_addr,
        "",
        today,
        "",
        recipient_addr,
        "",
        f"RE: Formal Credit Report Dispute — Round {round_.round_number}",
        f"    Pursuant to FCRA §§ 607(b), 609, 610, 611, 623(a)(5) | 15 U.S.C. §§ 1681e(b), 1681g, 1681h, 1681i, 1681s-2(a)(5)",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {client.first_name} {client.last_name}, hereby submit this formal dispute",
        "pursuant to my rights under the Fair Credit Reporting Act (FCRA), 15 U.S.C. § 1681",
        "et seq. Each section below contains specific legal demands that must be addressed",
        "within 30 days of receipt of this letter (FCRA § 611(a)(1)).",
        "",
        _SEP2,
        "SECTION 1 — PERSONAL INFORMATION CORRECTION",
        f"           Pursuant to FCRA § 607(b) — Maximum Possible Accuracy",
        _SEP2,
        "",
        "Pursuant to FCRA § 607(b), consumer reporting agencies must follow reasonable",
        "procedures to assure maximum possible accuracy of the information in consumer",
        "reports. I demand that you immediately review, correct, and/or delete the",
        "following categories of personal information that do not belong to me or are",
        "inaccurate:",
        "",
        "  • Any alternate names, aliases, or AKAs not authorized by me in writing",
        "  • Any prior addresses not associated with my actual residence history",
        "  • Any employer data that is inaccurate, outdated, or unverifiable",
        "  • Any Social Security number variations other than my correct SSN",
        "  • Any date of birth variations other than my correct date of birth",
        "",
        "Failure to maintain accurate personal identifiers may indicate a mixed file,",
        "identity error, or selective furnisher reporting — all actionable under FCRA.",
        "",
        _SEP2,
        "SECTION 2 — TRADELINE DISPUTES",
        "           Pursuant to FCRA §§ 611, 623(a)(5) | Metro 2 CRRG",
        _SEP2,
        "",
        "I formally dispute the accuracy and/or verifiability of the following accounts.",
        "For each account, I challenge the DOFD, payment status, balance, Metro 2",
        "compliance coding, and chain of title from the original creditor:",
        "",
    ]

    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(account number not provided)"
        lines += [
            f"ITEM {i}: {item.creditor_name.upper()}",
            f"  Account Number: {acct}",
            f"  Dispute Reason: {item.dispute_reason}",
            f"  Legal Basis: {item.fcra_basis or 'FCRA §§ 611, 623'}",
            f"  Specific Challenges:",
            f"    — Date of First Delinquency (DOFD): must be accurate per FCRA § 623(a)(5)",
            f"    — Payment/Account Status: must comply with Metro 2 CRRG status code standards",
            f"    — Balance Reporting: current balance and high balance must be accurate",
            f"    — Metro 2 Compliance: all fields must conform to CDIA Metro 2 CRRG",
            f"    — Chain of Title: if sold/assigned, full assignment chain must be verified",
            "",
        ]

    lines += [
        _SEP2,
        "SECTION 3 — NOTICE UNDER TransUnion LLC v. Ramirez, 594 U.S. ___ (2021)",
        "           Unverifiable Information = Concrete Injury",
        _SEP2,
        "",
        "The Supreme Court held in TransUnion LLC v. Ramirez, 594 U.S. ___ (2021) that",
        "the dissemination of inaccurate and unverifiable information in a consumer credit",
        "report constitutes a concrete, particularized injury sufficient for Article III",
        "standing. Any information you cannot verify through competent, first-hand evidence",
        "— not merely an electronic ping through e-OSCAR — must be deleted from my",
        "consumer file pursuant to FCRA § 611(a)(5).",
        "",
        "A 'rubber-stamp' or e-OSCAR electronic investigation without substantive review",
        "of underlying documents does not satisfy the FCRA's reinvestigation requirement.",
        "See Hinkle v. Midland Credit Mgmt., Inc., 827 F.3d 298 (4th Cir. 2016).",
        "",
        _SEP2,
        "SECTION 4 — METHOD OF VERIFICATION DEMAND",
        "           Pursuant to FCRA § 611(a)(6)(B)(iii)",
        _SEP2,
        "",
        "Upon completion of your investigation, I demand the following for each item",
        "investigated, pursuant to FCRA § 611(a)(6)(B)(iii):",
        "",
        "  1. The full name, address, and telephone number of the person or entity",
        "     who verified the information",
        "  2. The specific method used to verify (e.g., reviewed original contract,",
        "     reviewed payment history ledger) — NOT merely 'verified by data furnisher'",
        "  3. A description of the specific documents reviewed during verification",
        "  4. Confirmation that the investigation was conducted by a human reviewer,",
        "     not solely by automated e-OSCAR data matching",
        "",
        "Any verification that cannot be substantiated by competent evidence must result",
        "in deletion of the disputed item (FCRA § 611(a)(5)(A)).",
        "",
        _SEP2,
        "SECTION 5 — FULL CONSUMER FILE DISCLOSURE",
        "           Pursuant to FCRA §§ 609, 610 | 15 U.S.C. §§ 1681g, 1681h",
        _SEP2,
        "",
        "Pursuant to FCRA § 609 (Consumer Disclosure Rights) and § 610 (Conditions and",
        "Form of Disclosure), I demand a complete disclosure of my consumer file including:",
        "",
        "  • All information in my consumer file, including archived and suppressed data",
        "  • All soft inquiry records, including promotional and account review inquiries",
        "  • Complete Metro 2 data fields (full 426-character payment history records)",
        "  • Complete furnisher identification: name, address, account number, contact",
        "  • All source codes, subscriber codes, and internal notations",
        "  • All prior addresses and name variations maintained in your system",
        "  • Complete dispute history including prior dispute outcomes",
        "",
        _SEP2,
        "SECTION 6 — REQUIRED ACTION AND COMPLIANCE DEMAND",
        f"           30-Day Deadline: {today}",
        _SEP2,
        "",
        "Within 30 days of receipt of this letter (FCRA § 611(a)(1)), you must:",
        "",
        "  1. DELETE all information that cannot be verified through competent evidence",
        "     (FCRA § 611(a)(5)(A))",
        "  2. CORRECT all inaccurate personal identifiers in my consumer file",
        "  3. PROVIDE written notice of the results of your investigation",
        "  4. SEND a free copy of my updated consumer report if changes are made",
        "     (FCRA § 611(a)(6)(A))",
        "  5. NOTIFY all furnishers of any corrections or deletions made",
        "     (FCRA § 611(a)(6)(B)(i))",
    ] + _state_sol_notice(state) + [
        "",
        "WILLFUL NONCOMPLIANCE WARNING:",
        "Willful failure to comply with the FCRA subjects you to civil liability for",
        "statutory damages of $100-$1,000 per violation, punitive damages, and attorney's",
        "fees under FCRA § 616 (15 U.S.C. § 1681n). Reckless disregard of FCRA",
        "requirements constitutes willfulness. Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007).",
        "",
        _SEP,
        "I reserve all rights and remedies available under the FCRA, FDCPA, state",
        "consumer protection laws, and applicable case law.",
        "",
        "Sincerely,",
        "",
        "",
        f"{client.first_name} {client.last_name}",
        f"{client_addr}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: This letter is prepared for dispute purposes only. It does",
        "not constitute legal advice. No outcome is guaranteed. Consult a licensed",
        "attorney for legal guidance specific to your situation.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_debt_collector_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    """Debt Collector Playbook — Steps 1-4 combined validation + cease reporting demand."""
    recipient_name = round_.recipient_name or "Debt Collector"
    recipient_addr = recipient_name
    if round_.recipient_address:
        recipient_addr += "\n" + round_.recipient_address
    client_addr = _client_addr_block(client)
    state = (client.state or "").upper()

    lines = [
        client_addr,
        "",
        today,
        "",
        recipient_addr,
        "",
        f"RE: Debt Validation Request, Cease Reporting Demand, and Direct Furnisher Dispute",
        f"    Pursuant to FDCPA §§ 1692c(c), 1692e, 1692f, 1692g | FCRA §§ 611, 623",
        f"    Round {round_.round_number}",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {client.first_name} {client.last_name}, am writing regarding the debt(s)",
        "identified below. This letter serves multiple legal purposes under the Fair Debt",
        "Collection Practices Act (FDCPA) and the Fair Credit Reporting Act (FCRA).",
        "",
        _SEP2,
        "STEP 1 — FORMAL DEBT VALIDATION DEMAND",
        "         Pursuant to FDCPA § 1692g | 15 U.S.C. § 1692g",
        _SEP2,
        "",
        "Pursuant to FDCPA § 1692g, I formally dispute the validity of the debt(s) below",
        "and demand complete validation. You must CEASE ALL COLLECTION ACTIVITY, including",
        "credit reporting, until you have provided proper validation. Credit reporting is",
        "a form of communication under FDCPA § 1692a(2). See Edeh v. Midland Credit",
        "Management, Inc., 748 F.Supp.2d 1030 (D. Minn. 2010).",
        "",
        "I demand the following documentation for each account:",
        "  1. The name and address of the ORIGINAL CREDITOR",
        "  2. The ORIGINAL SIGNED CONTRACT or agreement creating the alleged debt",
        "  3. Complete CHAIN OF TITLE showing every assignment from original creditor to you",
        "     (each assignment agreement, purchase agreement, and bill of sale)",
        "  4. Complete ACCOUNTING of the alleged debt, including:",
        "     — Original balance at time of charge-off",
        "     — Itemization of all interest, fees, and penalties added",
        "     — Date and amount of any payments applied",
        "     — Current claimed balance with full calculation",
        "  5. The DATE OF FIRST DELINQUENCY (DOFD) with the original creditor",
        "     (FCRA § 623(a)(5))",
        "  6. Proof that the statute of limitations has NOT expired",
        "  7. Proof that your agency is LICENSED to collect debt in my state",
        "",
    ]

    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(account number not provided)"
        lines += [
            f"ACCOUNT {i}: {item.creditor_name.upper()}",
            f"  Account Number: {acct}",
            f"  Dispute: {item.dispute_reason}",
            f"  Legal Basis: {item.fcra_basis or 'FDCPA § 1692g, FCRA § 623'}",
            "",
        ]

    lines += [
        _SEP2,
        "STEP 2 — CEASE COMMUNICATION DEMAND",
        "         Pursuant to FDCPA § 1692c(c) | 15 U.S.C. § 1692c(c)",
        _SEP2,
        "",
        "Pursuant to FDCPA § 1692c(c), I hereby demand that you CEASE ALL COMMUNICATION",
        "with me regarding the debt(s) above, EXCEPT to:",
        "  1. Advise me that further collection efforts are being terminated",
        "  2. Notify me of specific remedies you intend to invoke",
        "  3. Provide the validation documents demanded in Step 1 above",
        "",
        "This demand includes, but is not limited to:",
        "  • All phone calls, letters, emails, and text messages",
        "  • All credit reporting updates that increase balance or worsen status",
        "  • Any transfer or sale of this debt to another collector",
        "",
        _SEP2,
        "STEP 3 — CREDIT REPORTING CHALLENGE (FDCPA § 1692a(2))",
        "         Credit Reporting = Collection Activity",
        _SEP2,
        "",
        "Pursuant to FDCPA § 1692a(2), 'communication' means the conveying of information",
        "regarding a debt directly or indirectly through any medium. Credit reporting is",
        "communication. See Edeh v. Midland Credit Management, Inc., 748 F.Supp.2d 1030",
        "(D. Minn. 2010). Continued credit reporting of an unvalidated debt constitutes:",
        "",
        "  • A false or misleading representation under FDCPA § 1692e",
        "  • An unfair practice under FDCPA § 1692f",
        "  • A violation of FCRA § 623(a)(3) (reporting after notice of dispute)",
        "",
        "You must instruct all consumer reporting agencies (Experian, Equifax, TransUnion,",
        "and Innovis) to SUPPRESS or DELETE this account pending validation.",
        "",
        _SEP2,
        "STEP 4 — DIRECT FURNISHER DISPUTE",
        "         Pursuant to FCRA § 623 | 15 U.S.C. § 1681s-2",
        _SEP2,
        "",
        "As a furnisher of credit information, you have an independent duty under FCRA",
        "§ 623 to report only accurate, complete, and verifiable information. I formally",
        "dispute the accuracy of the information reported to all consumer reporting agencies",
        "regarding the account(s) above. You must:",
        "",
        "  1. Investigate this dispute within 30 days (FCRA § 623(b)(1))",
        "  2. Review all relevant information provided",
        "  3. Report corrected information to all consumer reporting agencies",
        "  4. If information cannot be verified, DELETE it from all consumer reports",
    ] + _state_sol_notice(state) + [
        "",
        _SEP,
        "FAILURE TO COMPLY:",
        "Failure to validate and continued collection activity (including credit reporting)",
        "constitutes willful noncompliance with FDCPA and FCRA, exposing you to civil",
        "liability for actual damages, statutory damages ($100-$1,000 per FDCPA violation),",
        "punitive damages, and attorney's fees. Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007).",
        "",
        "Sincerely,",
        "",
        "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: This letter is for dispute purposes only. It does not",
        "constitute legal advice. No outcome is guaranteed. Consult a licensed attorney.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_cease_desist_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_name = round_.recipient_name or "Debt Collector"
    recipient_addr = recipient_name + ("\n" + round_.recipient_address if round_.recipient_address else "")
    client_addr = _client_addr_block(client)

    lines = [
        client_addr, "", today, "", recipient_addr, "",
        "RE: FORMAL CEASE AND DESIST — All Collection Communication",
        "    Pursuant to FDCPA § 1692c(c) | 15 U.S.C. § 1692c(c)",
        "",
        "NOTICE TO CEASE ALL COMMUNICATION",
        "",
        f"I, {client.first_name} {client.last_name}, hereby formally and unequivocally",
        "demand that you IMMEDIATELY CEASE ALL COMMUNICATION with me regarding any and",
        "all alleged debts, pursuant to the Fair Debt Collection Practices Act (FDCPA)",
        "§ 1692c(c), 15 U.S.C. § 1692c(c).",
        "",
        "This demand applies to ALL communication including:",
        "  • Telephone calls to any number associated with me",
        "  • Written correspondence to any address",
        "  • Email or electronic communication of any kind",
        "  • Text messages",
        "  • Contact through third parties",
        "  • Any credit reporting updates regarding the alleged debt",
        "",
        "Under FDCPA § 1692c(c), upon receipt of this notice you may ONLY contact me to:",
        "  1. Advise that further collection efforts are being terminated",
        "  2. Notify me of a specific remedy you intend to invoke",
        "",
        "CREDIT REPORTING IS COMMUNICATION:",
        "Continued reporting of any alleged debt to consumer reporting agencies after",
        "receipt of this cease notice constitutes continued collection communication under",
        "FDCPA § 1692a(2). See Edeh v. Midland Credit Management, Inc., 748 F.Supp.2d",
        "1030 (D. Minn. 2010). Any such reporting will be treated as a willful FDCPA",
        "violation subject to civil action.",
        "",
        "ACCOUNTS SUBJECT TO THIS DEMAND:",
    ]
    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(see above)"
        lines.append(f"  {i}. {item.creditor_name} — Account {acct}")

    lines += [
        "",
        "Violation of this cease demand will subject you to civil liability for:",
        "  • Actual damages",
        "  • Statutory damages up to $1,000 per violation (FDCPA § 1692k)",
        "  • Attorney's fees and court costs",
        "  • Punitive damages where willfulness is established",
        "",
        "GOVERN YOURSELF ACCORDINGLY.",
        "",
        "Sincerely,",
        "", "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: This letter is for dispute purposes only. Not legal advice.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_method_of_verification_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Credit Bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         round_.recipient_name or bureau_name)
    if round_.recipient_address and round_.bureau not in _BUREAU_ADDRESS:
        recipient_addr += "\n" + round_.recipient_address
    client_addr = _client_addr_block(client)

    lines = [
        client_addr, "", today, "", recipient_addr, "",
        "RE: Method of Verification (MOV) Demand — Prior Dispute Response",
        "    Pursuant to FCRA § 611(a)(6)(B)(iii) | 15 U.S.C. § 1681i(a)(6)(B)(iii)",
        "",
        f"To Whom It May Concern:",
        "",
        f"I, {client.first_name} {client.last_name}, received your response to my prior",
        "credit dispute indicating that the disputed information was 'verified.' I am",
        "NOT satisfied with this response and hereby demand a complete Method of Verification",
        "(MOV) pursuant to FCRA § 611(a)(6)(B)(iii).",
        "",
        "A mere statement that information was 'verified by the data furnisher' through",
        "an automated e-OSCAR system does NOT satisfy the FCRA's reinvestigation requirement.",
        "See Hinkle v. Midland Credit Mgmt., Inc., 827 F.3d 298 (4th Cir. 2016);",
        "Cushman v. Trans Union Corp., 115 F.3d 220 (3d Cir. 1997).",
        "",
        _SEP,
        "ITEMS FOR WHICH MOV IS DEMANDED:",
        _SEP,
        "",
    ]
    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(see dispute)"
        lines += [
            f"Item {i}: {item.creditor_name} — Account {acct}",
            f"  Original Dispute: {item.dispute_reason}",
            "",
        ]

    lines += [
        _SEP,
        "FOR EACH ITEM ABOVE, I DEMAND THE FOLLOWING:",
        _SEP,
        "",
        "  1. VERIFIER IDENTITY:",
        "     — Full legal name of the individual who conducted the verification",
        "     — Title and department of the verifier",
        "     — Complete contact information for the verifier",
        "",
        "  2. VERIFICATION METHOD:",
        "     — Specific method used (NOT 'e-OSCAR' or 'data furnisher confirmed')",
        "     — Whether a human reviewed original source documents",
        "     — Whether the investigation was conducted by an automated system only",
        "",
        "  3. DOCUMENTS REVIEWED:",
        "     — List of every specific document reviewed during verification",
        "     — Copies of any documents you relied upon to verify the information",
        "     — Identification of who provided these documents",
        "",
        "  4. TIMELINE:",
        "     — Date dispute was transmitted to the furnisher",
        "     — Date furnisher responded",
        "     — Date final determination was made",
        "",
        "Under TransUnion LLC v. Ramirez, 594 U.S. ___ (2021), unverifiable credit",
        "report information causes concrete injury. If you cannot provide the above",
        "information, the disputed data must be deleted (FCRA § 611(a)(5)(A)).",
        "",
        "You have 15 days from receipt of this demand to provide the requested information.",
        "",
        "Sincerely,",
        "", "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: Not legal advice. No outcome guaranteed. Consult an attorney.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_full_file_disclosure_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Credit Bureau").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(), round_.recipient_name or bureau_name)
    client_addr = _client_addr_block(client)

    lines = [
        client_addr, "", today, "", recipient_addr, "",
        "RE: Full Consumer File Disclosure Demand",
        "    Pursuant to FCRA §§ 609, 610 | 15 U.S.C. §§ 1681g, 1681h",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {client.first_name} {client.last_name}, hereby formally demand complete",
        "disclosure of all information in my consumer file pursuant to FCRA § 609",
        "(Consumer Disclosure Rights) and § 610 (Conditions and Form of Disclosure).",
        "",
        "COMPLETE DISCLOSURE DEMANDED:",
        "",
        "  1. ALL TRADELINE DATA:",
        "     — Every account in my current file",
        "     — All archived, suppressed, or deleted account records",
        "     — Complete Metro 2 formatted data (all 426-character payment history segments)",
        "     — All subscriber/furnisher codes and contact information",
        "",
        "  2. ALL INQUIRY DATA:",
        "     — Hard inquiries (with permissible purpose for each)",
        "     — Soft inquiries (promotional, account review, etc.)",
        "     — Complete furnisher identification for each inquiry",
        "",
        "  3. ALL PERSONAL INFORMATION:",
        "     — Every name variation maintained in my file",
        "     — Every address maintained in my file",
        "     — Every employer maintained in my file",
        "     — Every phone number maintained in my file",
        "     — Every SSN variation (partial) maintained in my file",
        "",
        "  4. DISPUTE HISTORY:",
        "     — All prior disputes and their outcomes",
        "     — All notices of dispute transmitted to furnishers",
        "     — All furnisher responses received",
        "",
        "  5. INTERNAL DATA:",
        "     — All internal codes, scores, or notations in my file",
        "     — All source codes identifying how information was received",
        "     — All fraud alerts or security freezes in my file",
        "",
        "  6. ARCHIVED DATA:",
        "     — All information previously deleted or archived",
        "     — Any information from files that were merged with mine",
        "     — Any mixed-file indicators or corrections made",
        "",
        "Please provide this disclosure in writing within 15 days. I reserve the right",
        "to use this information in subsequent dispute letters and legal proceedings.",
        "",
        "Sincerely,",
        "", "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: Not legal advice. No outcome guaranteed. Consult an attorney.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_failure_to_investigate_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    bureau_name = (round_.bureau or round_.recipient_name or "Bureau/Furnisher").capitalize()
    recipient_addr = _BUREAU_ADDRESS.get((round_.bureau or "").lower(),
                                         round_.recipient_name or bureau_name)
    if round_.recipient_address and round_.bureau not in _BUREAU_ADDRESS:
        recipient_addr += "\n" + round_.recipient_address
    client_addr = _client_addr_block(client)

    lines = [
        client_addr, "", today, "", recipient_addr, "",
        "RE: Notice of Failure to Investigate — CFPB Escalation Warning",
        "    Pursuant to FCRA §§ 611, 616, 617 | 15 U.S.C. §§ 1681i, 1681n, 1681o",
        "",
        "To Whom It May Concern:",
        "",
        f"I, {client.first_name} {client.last_name}, submitted a formal credit dispute",
        "more than 30 days ago regarding the accounts listed below. As of today,",
        "I have either received NO response, an inadequate response, or the disputed",
        "information continues to appear on my credit report unchanged.",
        "",
        "This constitutes a FAILURE TO INVESTIGATE under FCRA § 611(a)(1), which",
        "requires completion of reinvestigation within 30 days (or 45 days with",
        "supplemental information).",
        "",
        _SEP,
        "ACCOUNTS SUBJECT TO PRIOR UNRESOLVED DISPUTE:",
        _SEP,
        "",
    ]
    for i, item in enumerate(round_.items, 1):
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(see prior dispute)"
        lines += [
            f"Item {i}: {item.creditor_name} — Account {acct}",
            f"  Original Dispute: {item.dispute_reason}",
            f"  Status: UNRESOLVED",
            "",
        ]

    lines += [
        _SEP,
        "LEGAL CONSEQUENCES OF FAILURE TO INVESTIGATE:",
        _SEP,
        "",
        "Your failure to properly investigate and resolve my dispute exposes you to:",
        "",
        "  • Civil liability for WILLFUL noncompliance under FCRA § 616:",
        "    — Statutory damages: $100 to $1,000 PER VIOLATION",
        "    — Punitive damages (no cap for willful violations)",
        "    — Attorney's fees and court costs",
        "    — Standard: Reckless disregard of FCRA requirements = willfulness",
        "      (Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007))",
        "",
        "  • Civil liability for NEGLIGENT noncompliance under FCRA § 617:",
        "    — Actual damages sustained",
        "    — Attorney's fees and court costs",
        "",
        "DEMANDED IMMEDIATE ACTIONS:",
        "  1. Complete the required reinvestigation of all disputed items IMMEDIATELY",
        "  2. Delete all items that cannot be verified through competent evidence",
        "     (FCRA § 611(a)(5)(A))",
        "  3. Send written results of investigation within 5 business days",
        "  4. Provide updated consumer credit report",
        "",
        "ESCALATION NOTICE:",
        "If this matter is not resolved within 10 days of receipt of this letter,",
        "I will file formal complaints with:",
        "  • Consumer Financial Protection Bureau (CFPB)",
        "  • Federal Trade Commission (FTC)",
        "  • State Attorney General",
        "  • And pursue civil action in federal court",
        "",
        "PLEASE GOVERN YOURSELF ACCORDINGLY.",
        "",
        "Sincerely,",
        "", "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: Not legal advice. No outcome guaranteed. Consult an attorney.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_affidavit(client: AegisClient, case: AegisCase, today: str) -> str:
    state = (client.state or "YOUR STATE").upper()
    county = client.city or "YOUR COUNTY"
    full_name = f"{client.first_name} {client.last_name}"

    lines = [
        _SEP2,
        "CONSUMER AFFIDAVIT",
        "In Support of Credit Dispute and Identity Verification",
        _SEP2,
        "",
        f"STATE OF {state}            )",
        "                            )  SS:",
        f"COUNTY OF {county.upper():<20})",
        "",
        f"I, {full_name}, being of lawful age and duly sworn, do hereby state and",
        "affirm under penalty of perjury that the following is true and correct to",
        "the best of my knowledge, information, and belief:",
        "",
        "1. PERSONAL IDENTIFICATION",
        f"   Full Legal Name: {full_name}",
        f"   Current Address: {client.address or '[ADDRESS]'}, {client.city or ''}, {client.state or ''} {client.zip_code or ''}".strip(", "),
        f"   Date of Birth: {client.dob or '[DATE OF BIRTH]'}",
        f"   SSN Last 4: {'x' * 5}-{client.ssn_last4 or 'XXXX'}",
        "",
        "2. AUTHORIZATION",
        "   I authorize Cruel & Associates to act as my authorized representative",
        "   for all matters related to my consumer credit reports, disputes, and",
        "   correspondence with credit reporting agencies and data furnishers.",
        "   This authorization extends to all three major credit reporting agencies",
        "   (Experian, Equifax, TransUnion) and Innovis.",
        "",
        "3. STATEMENT OF FACTS",
        "   a) I have reviewed my consumer credit reports and dispute the accuracy",
        "      and/or verifiability of certain information appearing therein.",
        "",
        "   b) I have never authorized the reporting of inaccurate, unverifiable,",
        "      or obsolete information on my consumer credit reports.",
        "",
        "   c) Any account, tradeline, inquiry, or personal identifier that I have",
        "      identified as inaccurate in my dispute letters is in fact inaccurate,",
        "      unverifiable, or does not belong to me.",
        "",
        "   d) I have not filed for bankruptcy protection [MODIFY IF APPLICABLE].",
        "",
        "   e) I am a victim of [identity theft / mixed file / inaccurate reporting]",
        "      [SELECT AND MODIFY AS APPLICABLE].",
        "",
        "4. IMPACT STATEMENT",
        "   The inaccurate information appearing on my consumer credit report(s) has",
        "   caused the following harm:",
        "   • [Denial of credit — specify application(s)]",
        "   • [Higher interest rates or unfavorable terms]",
        "   • [Emotional distress and damage to reputation]",
        "   • [Loss of housing or employment opportunities]",
        "   [MODIFY AS APPLICABLE — DELETE ITEMS THAT DO NOT APPLY]",
        "",
        "5. IDENTITY VERIFICATION",
        "   I hereby certify that the information provided in this affidavit is",
        "   accurate and that I am the individual described herein.",
        "",
        _SEP,
        "ATTESTATION",
        _SEP,
        "",
        "I declare under penalty of perjury under the laws of the United States",
        "and the State of " + state + " that the foregoing is true and correct.",
        "",
        f"Executed this ______ day of _____________, 20____",
        "",
        "",
        "_" * 50,
        f"{full_name}",
        "Affiant",
        "",
        _SEP,
        "NOTARY ACKNOWLEDGMENT",
        _SEP,
        "",
        f"State of {state}",
        f"County of {county.capitalize()}",
        "",
        "Subscribed and sworn to before me this ______ day of _____________, 20____",
        "by " + full_name + ", who is personally known to me or who has produced",
        "_________________ as identification.",
        "",
        "",
        "_" * 50,
        "Notary Public Signature",
        "",
        "Printed Name: _______________________________",
        "",
        "My Commission Expires: ______________________",
        "",
        "[NOTARY SEAL]",
        "",
        _SEP,
        "COMPLIANCE NOTICE: This affidavit template is for informational purposes only.",
        "Have this document reviewed by a licensed attorney before signing.",
        "No outcome is guaranteed. This does not constitute legal advice.",
        _SEP,
    ]
    return "\n".join(lines)


def _make_dispute_letter(round_: DisputeRound, client: AegisClient, today: str) -> str:
    recipient_type = (round_.recipient_type or "bureau").lower()

    if recipient_type == "bureau":
        return _make_bureau_dispute_letter(round_, client, today)

    if recipient_type in ("collection_agency", "debt_buyer"):
        return _make_debt_collector_letter(round_, client, today)

    if recipient_type == "cease_desist":
        return _make_cease_desist_letter(round_, client, today)

    if recipient_type == "method_of_verification":
        return _make_method_of_verification_letter(round_, client, today)

    if recipient_type == "full_file_disclosure":
        return _make_full_file_disclosure_letter(round_, client, today)

    if recipient_type == "failure_to_investigate":
        return _make_failure_to_investigate_letter(round_, client, today)

    # Build recipient address block for remaining types
    if recipient_type == "cfpb":
        recipient_addr = "Consumer Financial Protection Bureau\nP.O. Box 27170\nWashington, DC 20038"
        re_line = "RE: Formal Complaint — Failure to Correct Inaccurate Credit Information"
        authority = "    Pursuant to FCRA §§ 611, 623"
        body_intro = [
            "I am filing this formal complaint because a prior dispute submitted to the",
            "credit bureau and/or furnisher was ignored or resulted in an insufficient",
            "investigation. The inaccurate information described below continues to appear",
            "on my credit report in violation of FCRA §§ 611 and 623. I am escalating",
            "to the Bureau and requesting federal investigation and enforcement action.",
        ]
        close_demands = [
            "I respectfully request that the CFPB:",
            "  1. Investigate the failure to comply with FCRA §§ 611 and 623",
            "  2. Direct all responsible parties to correct or delete inaccurate information",
            "  3. Take appropriate enforcement action under the Bureau's supervisory authority",
            "  4. Note this complaint in the public Consumer Complaint Database",
        ]

    elif recipient_type == "ftc":
        recipient_addr = "Federal Trade Commission\nConsumer Response Center\n600 Pennsylvania Avenue NW\nWashington, DC 20580"
        re_line = "RE: FTC Complaint — FCRA/FDCPA Violations"
        authority = "    Pursuant to FTC Act § 5 and FCRA"
        body_intro = [
            "I am submitting this complaint regarding unfair or deceptive acts and practices",
            "in connection with my consumer credit report. The parties identified below",
            "have engaged in conduct that violates the Fair Credit Reporting Act (FCRA)",
            "and the FTC Act § 5, which prohibits unfair or deceptive acts or practices.",
        ]
        close_demands = [
            "I request that the FTC:",
            "  1. Investigate the unfair and deceptive practices described above",
            "  2. Take enforcement action against the responsible parties",
            "  3. Require corrective action to remedy the harm caused",
        ]

    elif recipient_type == "state_ag":
        recipient_addr = round_.recipient_address or "State Attorney General\n[State Capital Address]"
        re_line = "RE: Consumer Protection Complaint — Credit Reporting Violations"
        authority = "    Pursuant to State UDAP Laws and FCRA"
        body_intro = [
            "I am submitting this complaint regarding violations of state consumer",
            "protection laws (UDAP statutes) and the federal Fair Credit Reporting Act",
            "(FCRA) committed by the parties identified below.",
        ]
        close_demands = [
            "I respectfully request that the Attorney General's office:",
            "  1. Investigate violations of state UDAP statutes and the FCRA",
            "  2. Take appropriate enforcement action",
            "  3. Require correction of all inaccurate information",
        ]

    elif recipient_type == "medical_provider":
        recipient_addr = (round_.recipient_name or "Medical Provider")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Medical Debt and HIPAA Privacy Violation"
        authority = "    Pursuant to FCRA § 605(a)(6), HIPAA 45 CFR § 164.502"
        body_intro = [
            "I formally dispute the medical debt below and notify you of a potential",
            "HIPAA privacy violation. Under FCRA § 605(a)(6) and CFPB 2022 medical debt",
            "rules, paid or settled medical debt and debt under $500 is subject to",
            "special credit reporting restrictions. Sharing PHI with CRAs without",
            "written authorization may constitute a HIPAA violation.",
        ]
        close_demands = [
            "I demand that you:",
            "  1. Cease all collection activity on the disputed medical debt",
            "  2. Instruct all CRAs to delete this account",
            "  3. Provide documentation of any PHI authorization signed by me",
            "  4. Confirm deletion in writing within 30 days",
            "",
            "Failure to comply may result in complaints to the CFPB, HHS Office",
            "for Civil Rights (HIPAA violations), and civil action.",
        ]

    elif recipient_type == "student_loan_servicer":
        recipient_addr = (round_.recipient_name or "Student Loan Servicer")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Student Loan Servicing Error and Inaccurate Reporting"
        authority = "    Pursuant to FCRA § 623, Higher Education Act § 455, CFPB Servicer Guidance"
        body_intro = [
            "I formally dispute inaccurate student loan information you have reported",
            "to consumer reporting agencies. Under FCRA § 623 and HEA § 455, you must",
            "accurately report payment history, forbearance periods, and balances.",
        ]
        close_demands = [
            "I demand that you:",
            "  1. Investigate and correct all inaccurate information within 30 days",
            "  2. Report corrections to all CRAs (FCRA § 623(b))",
            "  3. Provide written confirmation of all corrections",
        ]

    elif recipient_type == "auto_lender":
        recipient_addr = (round_.recipient_name or "Auto Lender")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: Dispute of Wrongful Repossession and Deficiency Balance"
        authority = "    Pursuant to UCC Article 9 §§ 609-614, FDCPA § 809(b), FCRA § 623"
        body_intro = [
            "I formally dispute the repossession and/or deficiency balance reported",
            "on my consumer credit report. Under UCC Article 9 §§ 609-614, a creditor",
            "must provide proper notice and conduct a commercially reasonable sale.",
            "Failure voids the deficiency balance claim.",
        ]
        close_demands = [
            "I demand proof of:",
            "  1. Proper pre-repossession notice (UCC Art. 9 and state law)",
            "  2. Commercially reasonable sale (UCC § 9-610)",
            "  3. Complete deficiency balance accounting",
            "  4. Correction of all CRA reporting (FCRA § 623)",
            "",
            "Failure to provide this documentation requires deletion from all credit reports.",
        ]

    elif recipient_type == "intent_to_sue":
        recipient_addr = (round_.recipient_name or "Respondent")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = "RE: NOTICE OF INTENT TO FILE CIVIL LAWSUIT — FCRA Violations"
        authority = "    Pursuant to FCRA §§ 616, 617 | Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007)"
        body_intro = [
            "NOTICE IS HEREBY GIVEN that I intend to file a civil lawsuit for violations",
            "of the Fair Credit Reporting Act (FCRA) §§ 616, 617. Your conduct satisfies",
            "the willfulness standard of Safeco Ins. Co. v. Burr, 551 U.S. 47 (2007)",
            "(reckless disregard = willfulness). Statutory damages: $100-$1,000 per",
            "violation plus punitive damages and attorney's fees.",
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
        authority = "    Pursuant to FCRA § 623"
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

    else:  # creditor or fallback
        recipient_addr = (round_.recipient_name or "Creditor")
        if round_.recipient_address:
            recipient_addr += "\n" + round_.recipient_address
        re_line = f"RE: Dispute of Inaccurate Account Information — Round {round_.round_number}"
        authority = "    Pursuant to FCRA § 623"
        body_intro = [
            "I formally dispute inaccurate information you have reported to consumer",
            "reporting agencies. Under FCRA § 623, furnishers must report accurate data",
            "and investigate disputes within 30 days.",
        ]
        close_demands = [
            "Please:",
            "  1. Correct any inaccurate information with all CRAs, OR",
            "  2. Delete the account if information cannot be verified",
            "",
            "Under FCRA § 623(b), provide written confirmation of corrections.",
        ]

    client_addr = _client_addr_block(client)

    lines = [
        client_addr, "", today, "", recipient_addr, "",
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
        acct = f"xxxx-{item.account_number_last4}" if item.account_number_last4 else "(account number not provided)"
        lines += [
            "",
            f"Item {i}: {item.creditor_name}",
            f"  Account: {acct}",
            f"  Dispute Reason: {item.dispute_reason}",
            f"  Legal Basis: {item.fcra_basis or 'FCRA § 623'}",
        ]

    lines += [
        "", _SEP, "",
    ] + close_demands + [
        "",
        "I reserve all rights and remedies available under applicable law.",
        "",
        "Sincerely,",
        "", "",
        f"{client.first_name} {client.last_name}",
        "",
        _SEP,
        "COMPLIANCE NOTICE: Not legal advice. No outcome guaranteed. Consult an attorney.",
        _SEP,
    ]
    return "\n".join(lines)


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
        "─" * 70,
        f"TRADELINE SUMMARY ({len(tradelines)} accounts)",
        "─" * 70,
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

    lines += ["", "─" * 70, f"FINDINGS ({len(findings)} total)", "─" * 70]
    for f in findings:
        lines.append(f"\n[{f.severity.upper()}] {f.title}")
        lines.append(f"  Type: {f.finding_type} | FCRA: {f.fcra_section or 'N/A'}")
        lines.append(f"  {f.description}")
        lines.append(f"  *** REQUIRES HUMAN REVIEW BEFORE ANY ACTION ***")

    lines += ["", "─" * 70, f"RECOMMENDED STRATEGY ({len(strategy)} items)", "─" * 70]
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
    """Generate and download a dispute letter for a specific round."""
    round_ = db.query(DisputeRound).filter(DisputeRound.id == round_id).first()
    if not round_:
        raise HTTPException(404, "Dispute round not found")
    # Allow certain letter types without items (e.g. full file disclosure, affidavit)
    no_items_ok = (round_.recipient_type or "").lower() in ("full_file_disclosure",)
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
    """Generate a consumer affidavit for the case client."""
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
