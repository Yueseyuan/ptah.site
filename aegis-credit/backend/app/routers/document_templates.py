"""CRUD router for DocumentTemplate — reusable {{variable}} templates for all 6 divisions.

Divisions: notary | credit | criminal | document | judgment | consulting
"""

import json
import re
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import DocumentTemplate, ServiceCase, User
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/templates", tags=["document_templates"])

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

VALID_DIVISIONS = {"notary", "credit", "criminal", "document", "judgment", "consulting"}
VALID_CATEGORIES = {"agreement", "letter", "report", "log", "form", "packet"}
VALID_TEMPLATE_TYPES = {"intake", "generated"}


class TemplateCreate(BaseModel):
    division_slug: str
    name: str
    description: Optional[str] = None
    content: str
    variables: Optional[List[str]] = None  # inferred from content when omitted
    category: str = "letter"
    template_type: str = "generated"
    is_active: bool = True


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[List[str]] = None
    category: Optional[str] = None
    template_type: Optional[str] = None
    is_active: Optional[bool] = None


class PreviewRequest(BaseModel):
    """Optional override values for preview rendering.  Missing keys get auto-filled."""
    sample_values: Optional[dict] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VAR_RE = re.compile(r"\{\{(\w+)\}\}")


def _extract_variables(content: str) -> List[str]:
    """Return unique variable names found in {{var}} placeholders, in order."""
    seen: dict[str, None] = {}
    for m in _VAR_RE.finditer(content):
        seen[m.group(1)] = None
    return list(seen)


def _render(content: str, values: dict) -> str:
    """Replace every {{var}} with the corresponding value from *values*."""
    def replacer(m: re.Match) -> str:
        return str(values.get(m.group(1), m.group(0)))

    return _VAR_RE.sub(replacer, content)


def _default_sample(var_name: str) -> str:
    """Generate a human-readable sample value for a variable name."""
    mapping = {
        "first_name": "Jane",
        "last_name": "Smith",
        "full_name": "Jane Smith",
        "client_name": "Jane Smith",
        "date": "July 1, 2026",
        "today": "July 1, 2026",
        "signature_date": "July 1, 2026",
        "address": "123 Main Street, Columbia, SC 29201",
        "city": "Columbia",
        "state": "South Carolina",
        "zip": "29201",
        "phone": "(803) 555-0100",
        "email": "jane.smith@example.com",
        "case_number": "SVC-000001",
        "invoice_number": "INV-000001",
        "amount": "$150.00",
        "fee": "$150.00",
        "service_type": "Notarization",
        "document_type": "Affidavit",
        "notary_name": "Maria Johnson",
        "notary_commission": "NC-2024-001234",
        "notary_expiry": "December 31, 2027",
        "attorney_name": "Robert Davis, Esq.",
        "attorney_firm": "Davis & Associates",
        "creditor_name": "Capital One Bank",
        "account_number": "****1234",
        "balance": "$2,450.00",
        "bureau": "Experian",
        "fcra_section": "15 U.S.C. § 1681i",
        "dispute_reason": "Account information is inaccurate",
        "assigned_to": "A. Cruel",
        "company_name": "Cruel & Associates",
        "company_address": "456 Service Lane, Columbia, SC 29201",
        "company_phone": "(803) 555-0200",
        "company_email": "info@cruelandassociates.com",
        "division": "Notary Division",
        "court_name": "Richland County Court of Common Pleas",
        "docket_number": "2026-CP-001234",
        "judgment_amount": "$5,000.00",
        "defendant_name": "ABC Corp.",
        "plaintiff_name": "Jane Smith",
        "conviction_date": "March 15, 2019",
        "offense": "Misdemeanor — no-contest plea",
        "expungement_basis": "S.C. Code § 17-22-910",
        "record_type": "Criminal Background",
        "notes": "N/A",
    }
    # Fuzzy fallback — try to match substrings
    lower = var_name.lower()
    for key, val in mapping.items():
        if key in lower or lower in key:
            return val
    # Generic fallback
    return f"[{var_name.replace('_', ' ').title()}]"


def _build_sample_values(variables: List[str], overrides: Optional[dict]) -> dict:
    values = {v: _default_sample(v) for v in variables}
    if overrides:
        values.update(overrides)
    return values


def _out(t: DocumentTemplate) -> dict:
    vars_list: List[str] = []
    if t.variables:
        try:
            vars_list = json.loads(t.variables)
        except Exception:
            vars_list = []
    return {
        "id": t.id,
        "division_slug": t.division_slug,
        "template_type": t.template_type,
        "name": t.name,
        "description": t.description,
        "content": t.content,
        "variables": vars_list,
        "category": t.category,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


# ---------------------------------------------------------------------------
# Default seed data — one representative template per division (expandable)
# ---------------------------------------------------------------------------

DEFAULT_TEMPLATES: List[dict] = [
    # ── NOTARY ────────────────────────────────────────────────────────────────
    {
        "division_slug": "notary",
        "template_type": "generated",
        "name": "Notary Journal Entry Confirmation",
        "description": "Confirmation letter sent to signer after a mobile notarization.",
        "category": "letter",
        "content": (
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "Date: {{date}}\n\n"
            "Dear {{full_name}},\n\n"
            "This letter confirms that on {{date}}, Notary Public {{notary_name}} "
            "(Commission No. {{notary_commission}}, expiring {{notary_expiry}}) "
            "notarized your {{document_type}} at the location on file.\n\n"
            "Journal Reference: {{case_number}}\n"
            "Fee Charged: {{fee}}\n\n"
            "Please retain this confirmation for your records. If you have any "
            "questions, contact us at {{company_phone}}.\n\n"
            "Sincerely,\n{{notary_name}}\nNotary Public, State of South Carolina"
        ),
    },
    {
        "division_slug": "notary",
        "template_type": "generated",
        "name": "Mobile Notary Service Agreement",
        "description": "Standard engagement agreement for mobile notary appointments.",
        "category": "agreement",
        "content": (
            "MOBILE NOTARY SERVICE AGREEMENT\n\n"
            "This Agreement is entered into as of {{date}} between {{company_name}} "
            "(\"Notary\") and {{full_name}} (\"Client\").\n\n"
            "1. SERVICES\nNotary agrees to travel to {{address}} to notarize the "
            "following document(s): {{document_type}}.\n\n"
            "2. FEES\nClient agrees to pay a service fee of {{fee}} which includes "
            "travel and state-mandated notarization fees.\n\n"
            "3. IDENTIFICATION\nClient must present valid government-issued photo "
            "identification at the time of signing.\n\n"
            "4. CANCELLATION\nCancellations made less than 2 hours before the "
            "scheduled appointment may incur a cancellation fee.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{notary_name}} (Notary)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}"
        ),
    },
    # ── CREDIT ────────────────────────────────────────────────────────────────
    {
        "division_slug": "credit",
        "template_type": "generated",
        "name": "Credit Bureau Dispute Letter",
        "description": "FCRA § 611 dispute letter to a credit bureau.",
        "category": "letter",
        "content": (
            "{{full_name}}\n"
            "{{address}}\n"
            "{{phone}}\n"
            "{{email}}\n\n"
            "Date: {{date}}\n\n"
            "{{bureau}} Credit Bureau\n"
            "Dispute Department\n\n"
            "RE: Dispute of Inaccurate Credit Information — {{fcra_section}}\n\n"
            "To Whom It May Concern:\n\n"
            "I am writing to dispute the following information in my credit file. "
            "The item(s) listed below are inaccurate or incomplete and must be "
            "investigated and corrected under the Fair Credit Reporting Act, "
            "{{fcra_section}}.\n\n"
            "Disputed Account:\n"
            "Creditor: {{creditor_name}}\n"
            "Account: {{account_number}}\n"
            "Reason for Dispute: {{dispute_reason}}\n\n"
            "Please investigate this matter and provide me with written results "
            "within 30 days as required by law.\n\n"
            "Sincerely,\n\n"
            "_____________________________\n"
            "{{full_name}}\n"
            "Case Reference: {{case_number}}"
        ),
    },
    {
        "division_slug": "credit",
        "template_type": "generated",
        "name": "Goodwill Deletion Request Letter",
        "description": "Goodwill letter asking a creditor to remove a derogatory mark.",
        "category": "letter",
        "content": (
            "{{full_name}}\n"
            "{{address}}\n"
            "{{phone}} | {{email}}\n\n"
            "Date: {{date}}\n\n"
            "{{creditor_name}}\nCustomer Relations Department\n\n"
            "RE: Goodwill Deletion Request — Account {{account_number}}\n\n"
            "Dear {{creditor_name}} Team,\n\n"
            "I have been a customer of {{creditor_name}} and I am writing to "
            "respectfully request a goodwill deletion of the negative mark "
            "associated with account {{account_number}} (balance: {{balance}}).\n\n"
            "I take full responsibility for the late payment and have since "
            "maintained a positive payment history. I respectfully ask that you "
            "consider removing this derogatory entry as a gesture of goodwill "
            "to allow me to move forward.\n\n"
            "Thank you for your time and consideration.\n\n"
            "Sincerely,\n\n"
            "_____________________________\n"
            "{{full_name}}"
        ),
    },
    # ── CRIMINAL ──────────────────────────────────────────────────────────────
    {
        "division_slug": "criminal",
        "template_type": "generated",
        "name": "Criminal Record Review Summary",
        "description": "Internal summary report of a client's criminal record findings.",
        "category": "report",
        "content": (
            "CRIMINAL RECORD REVIEW SUMMARY\n"
            "{{company_name}} — Criminal Division\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "Prepared By: {{assigned_to}}\n"
            "Date: {{date}}\n\n"
            "RECORD TYPE: {{record_type}}\n"
            "COURT: {{court_name}}\n"
            "DOCKET: {{docket_number}}\n"
            "OFFENSE: {{offense}}\n"
            "DISPOSITION DATE: {{conviction_date}}\n\n"
            "EXPUNGEMENT ANALYSIS\n"
            "Eligibility Basis: {{expungement_basis}}\n"
            "Recommendation: Review by licensed attorney required before proceeding.\n\n"
            "NOTES\n{{notes}}\n\n"
            "DISCLAIMER: This summary is for informational purposes only and does "
            "not constitute legal advice. Client has been referred to {{attorney_name}} "
            "at {{attorney_firm}} for legal guidance.\n\n"
            "Prepared by: {{assigned_to}}\n{{company_name}}"
        ),
    },
    {
        "division_slug": "criminal",
        "template_type": "generated",
        "name": "Attorney Referral Letter",
        "description": "Referral letter forwarding a client to a criminal defense attorney.",
        "category": "letter",
        "content": (
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "Date: {{date}}\n\n"
            "{{attorney_name}}\n"
            "{{attorney_firm}}\n\n"
            "RE: Client Referral — {{full_name}} (Case {{case_number}})\n\n"
            "Dear {{attorney_name}},\n\n"
            "We are referring our client, {{full_name}}, to your office for legal "
            "representation regarding a criminal record matter. Our preliminary "
            "review indicates potential eligibility for expungement under "
            "{{expungement_basis}}; however, this determination requires professional "
            "legal analysis.\n\n"
            "Please contact {{full_name}} at {{phone}} or {{email}} to schedule "
            "an initial consultation.\n\n"
            "Thank you for your assistance.\n\n"
            "Sincerely,\n{{assigned_to}}\n{{company_name}}"
        ),
    },
    # ── DOCUMENT ──────────────────────────────────────────────────────────────
    {
        "division_slug": "document",
        "template_type": "generated",
        "name": "Document Preparation Engagement Letter",
        "description": "Engagement letter for document preparation services.",
        "category": "agreement",
        "content": (
            "DOCUMENT PREPARATION ENGAGEMENT LETTER\n\n"
            "Date: {{date}}\n\n"
            "Client: {{full_name}}\n"
            "Address: {{address}}\n"
            "Phone: {{phone}}\n"
            "Email: {{email}}\n\n"
            "{{company_name}} agrees to prepare the following document(s) on your "
            "behalf:\n\n"
            "Document(s): {{document_type}}\n"
            "Service Fee: {{fee}}\n"
            "Estimated Delivery: 3–5 business days after receipt of all required "
            "information.\n\n"
            "IMPORTANT NOTICE: {{company_name}} is NOT a law firm and cannot "
            "provide legal advice. The documents prepared are based solely on the "
            "information you provide. We recommend consulting a licensed attorney "
            "for legal guidance.\n\n"
            "By signing below, you confirm the above information is accurate.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Preparer)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}"
        ),
    },
    {
        "division_slug": "document",
        "template_type": "generated",
        "name": "Document Completion Notice",
        "description": "Notice to client that their documents are ready for pickup or delivery.",
        "category": "letter",
        "content": (
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "Date: {{date}}\n\n"
            "Dear {{full_name}},\n\n"
            "Your document(s) are ready:\n\n"
            "Document Type: {{document_type}}\n"
            "Case Reference: {{case_number}}\n\n"
            "Please contact us at {{company_phone}} to arrange pickup or delivery. "
            "Balance due upon receipt: {{fee}}.\n\n"
            "Sincerely,\n{{assigned_to}}\n{{company_name}}"
        ),
    },
    # ── JUDGMENT ──────────────────────────────────────────────────────────────
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Judgment Review Report",
        "description": "Summary report of a civil judgment found during a client review.",
        "category": "report",
        "content": (
            "JUDGMENT REVIEW REPORT\n"
            "{{company_name}} — Judgment Division\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "Prepared By: {{assigned_to}}\n"
            "Date: {{date}}\n\n"
            "JUDGMENT DETAILS\n"
            "Court: {{court_name}}\n"
            "Docket: {{docket_number}}\n"
            "Plaintiff: {{plaintiff_name}}\n"
            "Defendant: {{defendant_name}}\n"
            "Judgment Amount: {{judgment_amount}}\n\n"
            "ANALYSIS\n"
            "This judgment was identified during the client's record review. "
            "Satisfaction, vacation, or negotiation options may be available. "
            "Referral to licensed counsel is recommended.\n\n"
            "NOTES\n{{notes}}\n\n"
            "DISCLAIMER: For informational purposes only. Not legal advice.\n\n"
            "Prepared by: {{assigned_to}}\n{{company_name}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Judgment Satisfaction Letter",
        "description": "Letter to court confirming a judgment has been satisfied.",
        "category": "letter",
        "content": (
            "{{full_name}}\n"
            "{{address}}\n"
            "{{phone}} | {{email}}\n\n"
            "Date: {{date}}\n\n"
            "{{court_name}}\nClerk of Court\n\n"
            "RE: Satisfaction of Judgment — Docket No. {{docket_number}}\n\n"
            "To Whom It May Concern:\n\n"
            "Please be advised that the judgment in the above-referenced matter, "
            "originally entered against {{defendant_name}} in the amount of "
            "{{judgment_amount}}, has been fully satisfied as of {{date}}.\n\n"
            "Kindly update the court record accordingly and issue a Certificate "
            "of Satisfaction.\n\n"
            "Sincerely,\n\n"
            "_____________________________\n"
            "{{plaintiff_name}}\n"
            "Case Reference: {{case_number}}"
        ),
    },
    # ── JUDGMENT (commercial recovery suite) ─────────────────────────────────
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Non-Lawyer Disclosure",
        "description": "Required disclosure that Cruel & Associates is not a law firm and does not provide legal advice.",
        "category": "form",
        "content": (
            "NON-LAWYER DISCLOSURE\n"
            "Cruel & Associates — Commercial Judgment Recovery\n\n"
            "Date: {{date}}\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n\n"
            "IMPORTANT NOTICE — PLEASE READ CAREFULLY\n\n"
            "Cruel & Associates (\"Company\") is NOT a law firm and does NOT provide "
            "legal advice or legal representation.\n\n"
            "The Company provides commercial judgment recovery, asset investigation, "
            "and related administrative support services only. The Company's staff "
            "are not licensed attorneys and cannot:\n"
            "  • Represent you in court\n"
            "  • Provide legal advice on your rights or obligations\n"
            "  • Interpret statutes or court orders\n"
            "  • File documents with a court on your behalf without attorney supervision\n\n"
            "You are encouraged to consult with a licensed attorney regarding any "
            "legal questions, enforcement actions requiring court filings, or matters "
            "where legal representation is required.\n\n"
            "By signing below, you confirm that you have read and understood this "
            "disclosure.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Company Representative)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}}\n{{company_address}}\n{{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Commercial Judgment Recovery Agreement",
        "description": "Engagement agreement for commercial judgment recovery services on a contingency or hybrid basis.",
        "category": "agreement",
        "content": (
            "COMMERCIAL JUDGMENT RECOVERY AGREEMENT\n\n"
            "This Agreement is entered into as of {{date}} between "
            "{{company_name}} (\"Recovery Company\") and {{full_name}} (\"Client\").\n\n"
            "1. SUBJECT JUDGMENT\n"
            "Court: {{court_name}}\n"
            "Docket No.: {{docket_number}}\n"
            "Judgment Against: {{defendant_name}}\n"
            "Original Amount: {{judgment_amount}}\n\n"
            "2. SCOPE OF SERVICES\n"
            "Recovery Company will use lawful post-judgment enforcement methods to "
            "attempt recovery of the judgment balance, which may include asset "
            "investigation, demand communications, settlement negotiations, and "
            "coordination with licensed attorneys for court-based enforcement actions.\n\n"
            "3. COMPENSATION\n"
            "Client agrees to pay Recovery Company a contingency fee equal to "
            "{{fee}} of all amounts recovered. No fee is owed if no recovery "
            "is made.\n\n"
            "4. AUTHORITY\n"
            "Client authorizes Recovery Company to communicate with the debtor, "
            "debtor's representatives, and third parties as necessary to pursue "
            "recovery within the limits of applicable law.\n\n"
            "5. NOT A LAW FIRM\n"
            "Recovery Company is NOT a law firm. Any enforcement action requiring "
            "court filings will be coordinated with or referred to a licensed attorney "
            "at Client's cost.\n\n"
            "6. TERM AND TERMINATION\n"
            "This Agreement remains in effect until the judgment is recovered, "
            "settled, deemed uncollectable, or either party provides 30 days' "
            "written notice of termination.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Recovery Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}}\n{{company_address}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Asset Investigation Authorization",
        "description": "Client authorization for Cruel & Associates to conduct a debtor asset investigation.",
        "category": "form",
        "content": (
            "ASSET INVESTIGATION AUTHORIZATION\n\n"
            "Date: {{date}}\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n\n"
            "I, {{full_name}}, hereby authorize {{company_name}} to conduct an "
            "asset investigation of the following judgment debtor:\n\n"
            "Debtor Name: {{defendant_name}}\n"
            "Judgment Amount: {{judgment_amount}}\n"
            "Court: {{court_name}} | Docket: {{docket_number}}\n\n"
            "The investigation may include searches of publicly available records, "
            "including but not limited to: real property records, UCC filings, "
            "corporate registration databases, court records, business license "
            "databases, and other lawful public information sources.\n\n"
            "I represent that I am authorized to collect on this judgment and "
            "that I will use the investigation results only for lawful debt "
            "collection purposes.\n\n"
            "_____________________________\n"
            "{{full_name}} (Client)\n"
            "Date: {{signature_date}}\n\n"
            "{{company_name}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Judgment Evaluation Worksheet",
        "description": "Internal worksheet for evaluating judgment collectability before accepting a case.",
        "category": "form",
        "content": (
            "JUDGMENT EVALUATION WORKSHEET\n"
            "{{company_name}} — Internal Use Only\n\n"
            "Evaluator: {{assigned_to}} | Date: {{date}} | Case No.: {{case_number}}\n\n"
            "=== JUDGMENT DETAILS ===\n"
            "Creditor/Client: {{plaintiff_name}}\n"
            "Debtor: {{defendant_name}}\n"
            "Court: {{court_name}} | Docket: {{docket_number}}\n"
            "Original Judgment Amount: {{judgment_amount}}\n"
            "Accrued Interest/Costs: $___________\n"
            "Total Estimated Balance: $___________\n"
            "Judgment Date: ___________\n"
            "Renewal Deadline: ___________\n\n"
            "=== DEBTOR PROFILE ===\n"
            "Business Type:  [ ] Corporation  [ ] LLC  [ ] Sole Prop  [ ] Individual\n"
            "Operating Status:  [ ] Active  [ ] Inactive  [ ] Dissolved  [ ] Unknown\n"
            "Bankruptcy History:  [ ] None  [ ] Discharged  [ ] Active  [ ] Unknown\n"
            "Prior Collection Attempts:  [ ] None  [ ] Unsuccessful  [ ] Partial\n\n"
            "=== ASSET INDICATORS ===\n"
            "Real Property:  [ ] Confirmed  [ ] Possible  [ ] None  [ ] Unknown\n"
            "Bank Accounts:  [ ] Confirmed  [ ] Possible  [ ] None  [ ] Unknown\n"
            "Business Revenue:  [ ] Active  [ ] Limited  [ ] None  [ ] Unknown\n"
            "Vehicles/Equipment:  [ ] Confirmed  [ ] Possible  [ ] None  [ ] Unknown\n"
            "UCC Filings / Existing Liens: ___________\n\n"
            "=== COLLECTABILITY SCORE ===\n"
            "Score (1–100): _____ / 100\n"
            "Recommended Action:\n"
            "  [ ] Accept — high collectability\n"
            "  [ ] Accept with investigation — moderate collectability\n"
            "  [ ] Decline — insufficient assets\n"
            "  [ ] Refer to counsel — complex enforcement required\n\n"
            "Notes: {{notes}}\n\n"
            "Evaluated by: {{assigned_to}}\n{{company_name}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Recovery Service Agreement (Hybrid Fee)",
        "description": "Engagement agreement for hybrid flat investigation fee + contingency model.",
        "category": "agreement",
        "content": (
            "RECOVERY SERVICE AGREEMENT — HYBRID FEE\n\n"
            "Date: {{date}}\n"
            "Client: {{full_name}} | Case No.: {{case_number}}\n\n"
            "SUBJECT JUDGMENT\n"
            "Court: {{court_name}} | Docket: {{docket_number}}\n"
            "Debtor: {{defendant_name}} | Amount: {{judgment_amount}}\n\n"
            "FEE STRUCTURE\n"
            "1. Investigation Fee: {{fee}} (due upon signing; non-refundable)\n"
            "   Covers: asset investigation, skip trace, public records search, "
            "collectability assessment, and written recovery recommendation.\n\n"
            "2. Contingency Fee: ___% of amounts recovered above the investigation fee.\n\n"
            "SERVICES INCLUDED\n"
            "• Debtor asset investigation\n"
            "• Collectability assessment and written report\n"
            "• Recovery strategy development\n"
            "• Demand communication drafting\n"
            "• Settlement negotiation support\n"
            "• Attorney referral for court-based enforcement\n\n"
            "NOT A LAW FIRM: {{company_name}} does not provide legal representation. "
            "Court filings require a licensed attorney.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Internal Case Checklist",
        "description": "Staff checklist for tracking all required steps in a commercial judgment recovery case.",
        "category": "form",
        "content": (
            "COMMERCIAL JUDGMENT RECOVERY — CASE CHECKLIST\n"
            "{{company_name}} | Case No.: {{case_number}} | Client: {{full_name}}\n"
            "Assigned To: {{assigned_to}} | Opened: {{date}}\n\n"
            "STEP 1 — CLIENT INTAKE\n"
            "  [ ] Judgment copy received\n"
            "  [ ] Case number and court confirmed\n"
            "  [ ] Debtor information collected\n"
            "  [ ] Prior collection efforts documented\n"
            "  [ ] Non-Lawyer Disclosure signed\n"
            "  [ ] Engagement agreement executed\n\n"
            "STEP 2 — JUDGMENT VERIFICATION\n"
            "  [ ] Judgment validity confirmed\n"
            "  [ ] Remaining balance verified\n"
            "  [ ] Renewal requirements noted\n"
            "  [ ] Jurisdiction and enforceability confirmed\n\n"
            "STEP 3 — COLLECTABILITY ASSESSMENT\n"
            "  [ ] Collectability Worksheet completed\n"
            "  [ ] Collectability Score assigned: _____ / 100\n"
            "  [ ] Decision made: Accept / Decline / Refer\n\n"
            "STEP 4 — ASSET INVESTIGATION\n"
            "  [ ] Real estate search completed\n"
            "  [ ] Corporate/business records searched\n"
            "  [ ] UCC filing search completed\n"
            "  [ ] Bankruptcy history checked\n"
            "  [ ] Investigation report prepared\n\n"
            "STEP 5 — RECOVERY STRATEGY\n"
            "  [ ] Demand letter sent (if appropriate)\n"
            "  [ ] Settlement negotiations initiated\n"
            "  [ ] Attorney referral made (if required)\n"
            "  [ ] Enforcement action plan documented\n\n"
            "STEP 6 — CASE MANAGEMENT\n"
            "  [ ] Client updates sent\n"
            "  [ ] Deadlines and renewal dates calendared\n"
            "  [ ] All communications logged\n"
            "  [ ] Costs tracked\n\n"
            "STEP 7 — CASE CLOSURE\n"
            "  [ ] Recovery amount documented\n"
            "  [ ] Fees calculated and collected\n"
            "  [ ] Settlement or satisfaction documented\n"
            "  [ ] Final report prepared\n"
            "  [ ] File closed and archived\n\n"
            "Reviewed by: {{assigned_to}}\n{{company_name}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Settlement Agreement",
        "description": "Template settlement agreement between creditor and debtor to resolve the judgment.",
        "category": "agreement",
        "content": (
            "SETTLEMENT AGREEMENT AND RELEASE\n\n"
            "This Settlement Agreement is entered into as of {{date}} between "
            "{{plaintiff_name}} (\"Creditor\") and {{defendant_name}} (\"Debtor\").\n\n"
            "RECITALS\n"
            "Creditor holds a judgment against Debtor entered by {{court_name}}, "
            "Docket No. {{docket_number}}, in the original amount of {{judgment_amount}} "
            "(the \"Judgment\").\n\n"
            "SETTLEMENT TERMS\n"
            "1. Settlement Amount: Debtor agrees to pay Creditor the total sum of "
            "$___________ (the \"Settlement Amount\") as full and final satisfaction "
            "of the Judgment.\n\n"
            "2. Payment Schedule:\n"
            "   Payment 1: $___________ due on ___________\n"
            "   Payment 2: $___________ due on ___________\n"
            "   (Lump sum / installments as negotiated)\n\n"
            "3. Release: Upon receipt of the full Settlement Amount, Creditor agrees "
            "to file a Satisfaction of Judgment with {{court_name}} and release all "
            "claims arising from the Judgment.\n\n"
            "4. Default: If Debtor fails to make any payment when due, the full "
            "Judgment balance becomes immediately due and payable.\n\n"
            "5. No Admission: This settlement does not constitute an admission of "
            "liability by either party.\n\n"
            "IMPORTANT: This document is prepared by {{company_name}}, which is NOT "
            "a law firm. Both parties are encouraged to have this agreement reviewed "
            "by a licensed attorney before signing.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{plaintiff_name}} (Creditor)\t\t{{defendant_name}} (Debtor)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "Prepared by: {{company_name}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Case Status Report",
        "description": "Periodic status report sent to the client summarizing recovery activity.",
        "category": "report",
        "content": (
            "CASE STATUS REPORT\n"
            "{{company_name}} — Judgment Recovery Division\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "Report Date: {{date}}\n"
            "Assigned Specialist: {{assigned_to}}\n\n"
            "JUDGMENT SUMMARY\n"
            "Debtor: {{defendant_name}}\n"
            "Court: {{court_name}} | Docket: {{docket_number}}\n"
            "Original Amount: {{judgment_amount}}\n\n"
            "CURRENT STATUS\n"
            "Workflow Step: ___________\n"
            "Collectability Score: _____ / 100\n"
            "Recovery to Date: $___________\n"
            "Outstanding Balance: $___________\n\n"
            "RECENT ACTIVITY\n"
            "{{notes}}\n\n"
            "NEXT STEPS\n"
            "1. ___________\n"
            "2. ___________\n"
            "3. ___________\n\n"
            "IMPORTANT NOTICE: {{company_name}} is not a law firm and does not "
            "provide legal advice. Court-based enforcement actions require a "
            "licensed attorney.\n\n"
            "Questions? Contact us at {{company_phone}} or {{company_email}}.\n\n"
            "{{company_name}}\n{{company_address}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Final Recovery Report",
        "description": "Closing report documenting recovery outcome, fees, and case closure.",
        "category": "report",
        "content": (
            "FINAL RECOVERY REPORT\n"
            "{{company_name}} — Judgment Recovery Division\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "Closing Date: {{date}}\n"
            "Assigned Specialist: {{assigned_to}}\n\n"
            "JUDGMENT\n"
            "Debtor: {{defendant_name}}\n"
            "Court: {{court_name}} | Docket: {{docket_number}}\n"
            "Original Judgment Amount: {{judgment_amount}}\n\n"
            "RECOVERY SUMMARY\n"
            "Total Recovered: $___________\n"
            "Company Fee ({{fee}}): $___________\n"
            "Net to Client: $___________\n"
            "Recovery Method: ___________\n"
            "Settlement / Full Payment: ___________\n\n"
            "CASE NOTES\n"
            "{{notes}}\n\n"
            "CLOSURE ACTIONS COMPLETED\n"
            "  [ ] Judgment satisfaction filed with court\n"
            "  [ ] Final payment confirmed\n"
            "  [ ] Client funds disbursed\n"
            "  [ ] File archived\n\n"
            "Thank you for trusting {{company_name}} with your recovery matter.\n\n"
            "{{assigned_to}}\n{{company_name}}\n{{company_phone}} | {{company_email}}"
        ),
    },
    # ── CONSULTING ────────────────────────────────────────────────────────────
    {
        "division_slug": "consulting",
        "template_type": "generated",
        "name": "Consulting Engagement Agreement",
        "description": "Engagement agreement for credit and financial consulting services.",
        "category": "agreement",
        "content": (
            "CONSULTING SERVICES AGREEMENT\n\n"
            "This Agreement is entered into as of {{date}} between "
            "{{company_name}} (\"Consultant\") and {{full_name}} (\"Client\").\n\n"
            "1. SCOPE OF SERVICES\n"
            "Consultant agrees to provide financial and credit consulting services "
            "as outlined in the attached service plan (Case No. {{case_number}}).\n\n"
            "2. TERM\nThis Agreement begins on {{date}} and continues until "
            "the services are completed or either party provides written notice "
            "of termination.\n\n"
            "3. FEES\nClient agrees to pay {{fee}} for the services described "
            "herein. Payment is due upon signing.\n\n"
            "4. NO LEGAL ADVICE\n{{company_name}} does not provide legal advice "
            "and is not a law firm. Any legal questions should be directed to "
            "a licensed attorney.\n\n"
            "5. CONFIDENTIALITY\nBoth parties agree to keep all client information "
            "confidential in accordance with applicable law.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Consultant)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}"
        ),
    },
    {
        "division_slug": "consulting",
        "template_type": "generated",
        "name": "Consulting Action Plan",
        "description": "Personalized action plan document delivered to client after intake.",
        "category": "packet",
        "content": (
            "PERSONALIZED ACTION PLAN\n"
            "{{company_name}}\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "Consultant: {{assigned_to}}\n"
            "Date: {{date}}\n\n"
            "OVERVIEW\n"
            "Based on your intake consultation, we have developed the following "
            "action plan to address your financial and credit goals.\n\n"
            "IMMEDIATE STEPS (0–30 Days)\n"
            "1. Obtain tri-bureau credit reports from AnnualCreditReport.com\n"
            "2. Complete the identification verification packet\n"
            "3. Schedule follow-up appointment\n\n"
            "SHORT-TERM GOALS (30–90 Days)\n"
            "1. Review all negative tradelines for accuracy\n"
            "2. Initiate disputes for any inaccurate items\n"
            "3. Establish or rebuild positive credit lines\n\n"
            "LONG-TERM GOALS (90+ Days)\n"
            "1. Monitor credit score progress monthly\n"
            "2. Implement budgeting and savings strategy\n"
            "3. Reassess plan at 90-day review\n\n"
            "NOTES\n{{notes}}\n\n"
            "DISCLAIMER: This plan is for informational purposes only and does "
            "not constitute legal or financial advice.\n\n"
            "Consultant: {{assigned_to}}\n{{company_name}}\n{{company_phone}}"
        ),
    },
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/")
def list_templates(
    division: Optional[str] = None,
    category: Optional[str] = None,
    active: Optional[bool] = True,
    db: Session = Depends(get_db),
):
    """List templates with optional filters: ?division=credit&category=letter&active=true"""
    q = db.query(DocumentTemplate)
    if division is not None:
        q = q.filter(DocumentTemplate.division_slug == division)
    if category is not None:
        q = q.filter(DocumentTemplate.category == category)
    if active is not None:
        q = q.filter(DocumentTemplate.is_active == active)
    return [_out(t) for t in q.order_by(DocumentTemplate.division_slug, DocumentTemplate.name).all()]


@router.post("/seed", status_code=201)
def seed_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create default templates for all 6 divisions if none exist yet.

    Idempotent — skips any template whose (division_slug, name) pair is already
    present in the database.
    """
    created = []
    skipped = []

    for tpl_data in DEFAULT_TEMPLATES:
        existing = (
            db.query(DocumentTemplate)
            .filter(
                DocumentTemplate.division_slug == tpl_data["division_slug"],
                DocumentTemplate.name == tpl_data["name"],
            )
            .first()
        )
        if existing:
            skipped.append(tpl_data["name"])
            continue

        content = tpl_data["content"]
        variables = _extract_variables(content)

        tpl = DocumentTemplate(
            division_slug=tpl_data["division_slug"],
            template_type=tpl_data.get("template_type", "generated"),
            name=tpl_data["name"],
            description=tpl_data.get("description"),
            content=content,
            variables=json.dumps(variables),
            category=tpl_data.get("category", "letter"),
            is_active=True,
        )
        db.add(tpl)
        created.append(tpl_data["name"])

    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="SEED",
        resource_type="document_template",
        detail=f"Created {len(created)} default templates; skipped {len(skipped)}",
    )

    return {
        "created": len(created),
        "skipped": len(skipped),
        "templates_created": created,
        "templates_skipped": skipped,
    }


@router.post("/", status_code=201)
def create_template(
    data: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new document template."""
    if data.division_slug not in VALID_DIVISIONS:
        raise HTTPException(
            400,
            f"Invalid division_slug '{data.division_slug}'. "
            f"Must be one of: {', '.join(sorted(VALID_DIVISIONS))}",
        )
    if data.category not in VALID_CATEGORIES:
        raise HTTPException(
            400,
            f"Invalid category '{data.category}'. "
            f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}",
        )
    if data.template_type not in VALID_TEMPLATE_TYPES:
        raise HTTPException(
            400,
            f"Invalid template_type '{data.template_type}'. "
            f"Must be one of: {', '.join(sorted(VALID_TEMPLATE_TYPES))}",
        )

    # Auto-detect variables from content when not supplied
    variables = data.variables if data.variables is not None else _extract_variables(data.content)

    tpl = DocumentTemplate(
        division_slug=data.division_slug,
        template_type=data.template_type,
        name=data.name,
        description=data.description,
        content=data.content,
        variables=json.dumps(variables),
        category=data.category,
        is_active=data.is_active,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)

    log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="CREATE",
        resource_type="document_template",
        resource_id=tpl.id,
        detail=f"Created template '{tpl.name}' ({tpl.division_slug}/{tpl.category})",
    )

    return _out(tpl)


@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Fetch a single template by ID."""
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")
    return _out(tpl)


@router.put("/{template_id}")
def update_template(
    template_id: int,
    data: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Full or partial update of a template.  Omitted fields are left unchanged."""
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")

    updates = data.model_dump(exclude_unset=True)

    if "division_slug" in updates and updates["division_slug"] not in VALID_DIVISIONS:
        raise HTTPException(400, f"Invalid division_slug '{updates['division_slug']}'")
    if "category" in updates and updates["category"] not in VALID_CATEGORIES:
        raise HTTPException(400, f"Invalid category '{updates['category']}'")
    if "template_type" in updates and updates["template_type"] not in VALID_TEMPLATE_TYPES:
        raise HTTPException(400, f"Invalid template_type '{updates['template_type']}'")

    for field, value in updates.items():
        if field == "variables":
            # Accept list; serialise to JSON
            tpl.variables = json.dumps(value) if value is not None else None
        else:
            setattr(tpl, field, value)

    # If content changed but variables were not explicitly supplied, re-derive them
    if "content" in updates and "variables" not in updates:
        tpl.variables = json.dumps(_extract_variables(tpl.content))

    db.commit()
    db.refresh(tpl)

    log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="UPDATE",
        resource_type="document_template",
        resource_id=tpl.id,
        detail=f"Updated template '{tpl.name}' — fields: {list(updates.keys())}",
    )

    return _out(tpl)


@router.delete("/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Permanently delete a template."""
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")

    name = tpl.name
    db.delete(tpl)
    db.commit()

    log_action(
        db,
        user_id=current_user.id,
        username=current_user.username,
        action="DELETE",
        resource_type="document_template",
        resource_id=template_id,
        detail=f"Deleted template '{name}'",
    )


@router.post("/{template_id}/preview")
def preview_template(
    template_id: int,
    body: Optional[PreviewRequest] = None,
    db: Session = Depends(get_db),
):
    """Render the template with sample data and return the resulting text.

    Optionally supply ``sample_values`` in the request body to override specific
    variables.  Any variable not covered by the overrides receives a sensible
    auto-generated sample value.
    """
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(404, "Template not found")

    # Determine variables to fill
    variables: List[str] = []
    if tpl.variables:
        try:
            variables = json.loads(tpl.variables)
        except Exception:
            variables = []

    # Always re-scan the content in case stored variables list is stale
    detected = _extract_variables(tpl.content)
    # Merge: stored list takes ordering priority, then add any new ones
    all_vars = list(dict.fromkeys(variables + detected))

    overrides = (body.sample_values if body else None) or {}
    sample_values = _build_sample_values(all_vars, overrides)

    rendered = _render(tpl.content, sample_values)

    return {
        "template_id": tpl.id,
        "template_name": tpl.name,
        "division_slug": tpl.division_slug,
        "category": tpl.category,
        "variables_used": all_vars,
        "sample_values": sample_values,
        "rendered_text": rendered,
    }
