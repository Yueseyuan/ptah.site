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

VALID_DIVISIONS = {"notary", "credit", "criminal", "document", "judgment", "consulting", "overages"}
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
        # Overages
        "county": "Broward County",
        "parcel_folio": "514210-00-1234",
        "tax_deed_number": "TD-2024-001234",
        "property_description": "Lot 5, Block 12, Shady Pines Subdivision",
        "estimated_surplus": "$18,450.00",
        "opening_bid": "$42,000.00",
        "sale_price": "$60,450.00",
        "fee_percentage": "40%",
        "client_percentage": "60%",
        "owner_name": "James R. Carter",
        "state": "Florida",
        "docket_number": "2024-TX-001234",
        "court_name": "Broward County Clerk of Court",
        "judgment_amount": "$18,450.00",
        "defendant_name": "James R. Carter",
        "plaintiff_name": "Broward County Tax Collector",
        # Extended overages / estate fields
        "claim_amount": "$18,450.00",
        "cost_cap": "$500.00",
        "deceased_name": "Robert James Carter",
        "deceased_date": "January 15, 2023",
        "heir_relationship": "Son",
        "escheat_date": "September 30, 2026",
        "entity_name": "Carter Family Trust",
        "signor_name": "James R. Carter, Jr.",
        "signor_title": "Trustee",
        "tax_deed_year": "2024",
        "term": "August Term 2024",
        "new_plaintiff_name": "Cruel & Associates Recovery LLC",
        "attorney_id": "12248",
        "attorney_firm": "Cruel & Associates",
        "notary_fee": "$150.00",
        "your_website": "www.cruelandassociates.com",
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
    # ── OVERAGES ──────────────────────────────────────────────────────────────
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Non-Lawyer Disclosure (Tax Overage Recovery)",
        "description": "Required disclosure that Cruel & Associates is not a law firm for excess proceeds cases.",
        "category": "form",
        "content": (
            "NON-LAWYER DISCLOSURE — TAX OVERAGE RECOVERY\n"
            "Cruel & Associates\n\n"
            "Date: {{date}}\n"
            "Former Owner: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "County: {{county}}\n\n"
            "IMPORTANT NOTICE — PLEASE READ CAREFULLY\n\n"
            "Cruel & Associates (\"Company\") is NOT a law firm and does NOT provide "
            "legal advice or legal representation.\n\n"
            "The Company assists former property owners in identifying and recovering "
            "tax deed surplus funds (excess proceeds) from county clerks on a "
            "contingency basis. Company staff are NOT licensed attorneys and cannot:\n"
            "  • Represent you in court or any legal proceeding\n"
            "  • Provide legal advice on your rights or obligations\n"
            "  • Guarantee recovery of any funds\n"
            "  • Interpret statutes, court orders, or title matters\n\n"
            "Surplus fund recovery may involve competing claimants, lienholders, "
            "or other parties with legal priority. You are encouraged to consult a "
            "licensed attorney before proceeding if you have concerns.\n\n"
            "By signing below, you confirm that you have read and understood this "
            "disclosure and wish to proceed.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Former Owner)\t\t{{assigned_to}} (Company Representative)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}}\n{{company_address}}\n{{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Asset Recovery Contingency Agreement",
        "description": "Contingency fee agreement for tax deed surplus fund recovery services.",
        "category": "agreement",
        "content": (
            "TAX OVERAGE RECOVERY — CONTINGENCY AGREEMENT\n\n"
            "This Agreement is entered into as of {{date}} between "
            "{{company_name}} (\"Recovery Company\") and {{full_name}} (\"Client\").\n\n"
            "1. SURPLUS FUND CLAIM\n"
            "County: {{county}}\n"
            "Parcel / Folio: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Property: {{property_description}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "2. SCOPE OF SERVICES\n"
            "Recovery Company will research the surplus claim, prepare documentation, "
            "assist Client in completing and submitting the claim to the appropriate "
            "county authority, and coordinate all follow-up until funds are released.\n\n"
            "3. CONTINGENCY FEE\n"
            "Client agrees to pay Recovery Company a fee equal to {{fee}} of all "
            "surplus funds successfully recovered on Client's behalf. No fee is owed "
            "if no funds are recovered.\n\n"
            "4. AUTHORIZATION\n"
            "Client authorizes Recovery Company to communicate with the county clerk, "
            "tax collector, and other government offices on Client's behalf regarding "
            "this specific surplus claim.\n\n"
            "5. NOT A LAW FIRM\n"
            "Recovery Company is NOT a law firm. If legal complications arise — "
            "including competing claims requiring court resolution — an attorney "
            "referral will be made. Attorney fees, if any, are separate and not "
            "included in this agreement.\n\n"
            "6. TERM\n"
            "This Agreement remains in effect until the claim is resolved, funds are "
            "disbursed, the claim is denied, or either party provides written notice "
            "of termination.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Recovery Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}}\n{{company_address}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Authorization to Recover Funds",
        "description": "Client authorization allowing Cruel & Associates to act on their behalf with the county.",
        "category": "form",
        "content": (
            "AUTHORIZATION TO RECOVER SURPLUS FUNDS\n\n"
            "Date: {{date}}\n"
            "Case No.: {{case_number}}\n\n"
            "I, {{full_name}}, the former owner of the property described below, "
            "hereby authorize {{company_name}} to act as my authorized representative "
            "for the purpose of recovering tax deed surplus funds held by:\n\n"
            "County: {{county}}\n"
            "Property Address / Description: {{property_description}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "This authorization permits {{company_name}} to:\n"
            "  • Request and obtain records from the county clerk and tax collector\n"
            "  • Submit surplus fund claim forms on my behalf\n"
            "  • Communicate with county officials regarding this claim\n"
            "  • Receive and disburse recovered funds per the contingency agreement\n\n"
            "This authorization does NOT grant {{company_name}} authority to sign "
            "legal pleadings, appear in court, or provide legal advice on my behalf.\n\n"
            "Valid government-issued ID on file: [ ] Yes  [ ] No\n\n"
            "_____________________________\n"
            "{{full_name}} (Former Owner)\n"
            "Date: {{signature_date}}\n\n"
            "{{company_name}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Surplus Recovery Client Intake Sheet",
        "description": "Intake form capturing all required case details for a tax overage recovery case.",
        "category": "form",
        "content": (
            "SURPLUS RECOVERY CLIENT INTAKE SHEET\n"
            "{{company_name}}\n\n"
            "Case No.: {{case_number}}\n"
            "Date: {{date}}\n"
            "Intake Specialist: {{assigned_to}}\n\n"
            "=== CLIENT INFORMATION ===\n"
            "Former Owner Name: {{full_name}}\n"
            "Phone: {{phone}}\n"
            "Email: {{email}}\n"
            "Mailing Address: {{address}}\n\n"
            "=== PROPERTY INFORMATION ===\n"
            "County: {{county}}\n"
            "Property Description: {{property_description}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Tax Sale Date: ___________\n"
            "Opening Bid: $___________\n"
            "Final Sale Price: $___________\n"
            "Estimated Surplus: $___________\n\n"
            "=== CASE QUALIFIERS ===\n"
            "Is client the recorded owner at time of sale?  [ ] Yes  [ ] No  [ ] Unknown\n"
            "Are there known liens or mortgages on the property?  [ ] Yes  [ ] No  [ ] Unknown\n"
            "Any bankruptcy history?  [ ] Yes  [ ] No\n"
            "Any known competing claimants?  [ ] Yes  [ ] No\n"
            "Claim filed previously?  [ ] Yes (date: _________)  [ ] No\n"
            "Claim deadline (if known): ___________\n\n"
            "=== DOCUMENTS COLLECTED ===\n"
            "  [ ] Government-issued ID\n"
            "  [ ] Proof of ownership (deed, tax records)\n"
            "  [ ] Non-Lawyer Disclosure signed\n"
            "  [ ] Contingency Agreement signed\n"
            "  [ ] Authorization to Recover Funds signed\n\n"
            "Notes: {{notes}}\n\n"
            "Completed by: {{assigned_to}}\n{{company_name}}"
        ),
    },
    # ── OVERAGES — 9 legal document templates ─────────────────────────────────
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Assignment of Rights",
        "description": "Assigns the former owner's rights to recover tax deed surplus funds to Cruel & Associates.",
        "category": "agreement",
        "content": (
            "ASSIGNMENT OF RIGHTS TO SURPLUS FUNDS\n\n"
            "This Assignment of Rights (\"Assignment\") is entered into as of {{date}} by and "
            "between {{full_name}} (\"Assignor\") and {{company_name}} (\"Assignee\").\n\n"
            "RECITALS\n"
            "Assignor was the former owner of the real property described as:\n"
            "Property Description: {{property_description}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "County: {{county}}, State: {{state}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n\n"
            "The above property was sold at a tax deed sale, resulting in surplus / excess "
            "proceeds currently held by the {{county}} Clerk of Court in the estimated "
            "amount of {{estimated_surplus}} (\"Surplus Funds\").\n\n"
            "ASSIGNMENT\n"
            "For good and valuable consideration, Assignor hereby assigns, transfers, and "
            "conveys to Assignee all of Assignor's right, title, and interest in and to "
            "the Surplus Funds, including the right to file a claim, receive payment, and "
            "execute any documents necessary to recover the Surplus Funds from the county.\n\n"
            "COMPENSATION\n"
            "In consideration of Assignee's recovery services, Assignee shall be entitled "
            "to retain {{fee_percentage}} of all Surplus Funds recovered. The remaining "
            "{{client_percentage}} shall be remitted to Assignor within 10 business days "
            "of receipt.\n\n"
            "REPRESENTATIONS\n"
            "Assignor represents that: (a) Assignor is the lawful owner of the claim to the "
            "Surplus Funds; (b) Assignor has not previously assigned these rights to any "
            "other party; (c) Assignor is not aware of any competing claims or legal holds "
            "on the Surplus Funds, except as disclosed to Assignee.\n\n"
            "NON-ATTORNEY NOTICE\n"
            "{{company_name}} is NOT a law firm and does not provide legal advice. "
            "Assignor is encouraged to consult a licensed attorney before signing.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Assignor)\t\t\t{{assigned_to}} (Assignee / Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Assignment of Judgment",
        "description": "Assigns a judgment lien or claim right related to a surplus fund case.",
        "category": "agreement",
        "content": (
            "ASSIGNMENT OF JUDGMENT\n\n"
            "This Assignment of Judgment (\"Assignment\") is entered into as of {{date}} "
            "by and between {{full_name}} (\"Assignor\") and {{company_name}} (\"Assignee\").\n\n"
            "JUDGMENT DETAILS\n"
            "Court: {{court_name}}\n"
            "Case/Docket No.: {{docket_number}}\n"
            "Original Judgment Amount: {{judgment_amount}}\n"
            "Judgment Debtor: {{defendant_name}}\n"
            "County: {{county}}, State: {{state}}\n\n"
            "SURPLUS / CLAIM CONTEXT\n"
            "Parcel / Folio: {{parcel_folio}} | Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "ASSIGNMENT\n"
            "For good and valuable consideration, Assignor hereby irrevocably assigns, "
            "transfers, and conveys to Assignee all right, title, and interest in the "
            "above-referenced judgment, including all rights to enforce, collect, and "
            "execute upon the judgment in connection with any surplus fund claim or "
            "other recovery action.\n\n"
            "CONSIDERATION\n"
            "Assignee shall remit to Assignor {{client_percentage}} of any amounts "
            "collected pursuant to this judgment, after deducting Assignee's fee of "
            "{{fee_percentage}} and any documented recovery costs.\n\n"
            "REPRESENTATIONS\n"
            "Assignor warrants that: (a) Assignor has full authority to assign the "
            "judgment; (b) the judgment has not been previously assigned; (c) the "
            "judgment has not been satisfied, vacated, or stayed.\n\n"
            "NON-ATTORNEY NOTICE: {{company_name}} is NOT a law firm. Legal enforcement "
            "actions may require referral to a licensed attorney at additional cost.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Assignor)\t\t\t{{assigned_to}} (Assignee)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Fee Agreement (60/40 Contingency)",
        "description": "Contingency fee agreement where client receives 60% and company retains 40% of recovered surplus.",
        "category": "agreement",
        "content": (
            "FEE AGREEMENT — CONTINGENCY BASIS (60/40)\n\n"
            "This Fee Agreement (\"Agreement\") is made as of {{date}} between "
            "{{company_name}} (\"Recovery Company\") and {{full_name}} (\"Client\").\n\n"
            "SURPLUS FUND CASE DETAILS\n"
            "County: {{county}} | State: {{state}}\n"
            "Parcel / Folio: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Property: {{property_description}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "FEE STRUCTURE\n"
            "This is a contingency arrangement — NO UPFRONT FEE is charged.\n\n"
            "  Client Share:   60% of all surplus funds recovered\n"
            "  Company Fee:    40% of all surplus funds recovered\n\n"
            "If no funds are recovered, Client owes nothing. The Company absorbs all "
            "research, skip-trace, documentation, and filing costs.\n\n"
            "PAYMENT TERMS\n"
            "Upon recovery of surplus funds, Recovery Company shall:\n"
            "  1. Provide Client with a full written accounting\n"
            "  2. Remit 60% of net recovered funds to Client within 10 business days\n"
            "  3. Retain 40% as the Company's contingency fee\n\n"
            "SCOPE OF SERVICES (INCLUDED AT NO EXTRA CHARGE)\n"
            "  • Surplus fund verification and records research\n"
            "  • Owner locate / skip trace\n"
            "  • Document preparation (claim forms, authorization letters)\n"
            "  • County submission coordination\n"
            "  • Follow-up with county clerk through disbursement\n\n"
            "SERVICES NOT INCLUDED\n"
            "  • Court appearances or legal representation (requires licensed attorney)\n"
            "  • Probate or estate proceedings\n"
            "  • Resolution of competing claims (attorney referral at Client's option)\n\n"
            "NON-ATTORNEY DISCLOSURE\n"
            "{{company_name}} is NOT a law firm and does NOT provide legal advice. "
            "This Agreement is for document preparation and administrative recovery assistance only.\n\n"
            "TERM\n"
            "This Agreement remains in effect for 24 months or until the claim is resolved, "
            "denied, or either party provides 30 days' written notice of termination.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Recovery Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "Case No.: {{case_number}}\n"
            "{{company_name}} | {{company_address}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Limited Power of Attorney (Surplus Claim)",
        "description": "Grants Cruel & Associates limited authority to act on the former owner's behalf for the surplus claim.",
        "category": "form",
        "content": (
            "LIMITED POWER OF ATTORNEY\n"
            "(Surplus Fund Claim Only)\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "KNOW ALL PERSONS BY THESE PRESENTS, that I, {{full_name}} "
            "(\"Principal\"), residing at {{address}}, do hereby appoint "
            "{{company_name}}, located at {{company_address}} (\"Agent\"), as my "
            "true and lawful Attorney-in-Fact for the LIMITED purpose described below.\n\n"
            "AUTHORITY GRANTED\n"
            "This Limited Power of Attorney authorizes Agent to act on my behalf "
            "solely for the following purpose:\n\n"
            "  Recovery of tax deed surplus / excess proceeds for the property:\n"
            "  Property: {{property_description}}\n"
            "  Parcel / Folio: {{parcel_folio}}\n"
            "  Tax Deed No.: {{tax_deed_number}}\n"
            "  County: {{county}}, State: {{state}}\n"
            "  Estimated Surplus: {{estimated_surplus}}\n\n"
            "Specifically, Agent is authorized to:\n"
            "  • File surplus fund claim forms with the {{county}} Clerk of Court\n"
            "  • Execute claim submission documents on Principal's behalf\n"
            "  • Communicate with county officials regarding this specific claim\n"
            "  • Receive, endorse, and deposit surplus fund checks solely for "
            "disbursement per the Fee Agreement\n\n"
            "LIMITATIONS\n"
            "This Power of Attorney is STRICTLY LIMITED to the surplus fund claim "
            "described above. It does NOT authorize Agent to:\n"
            "  • File legal pleadings or appear in court\n"
            "  • Incur debts or obligations on behalf of Principal\n"
            "  • Convey, mortgage, or otherwise encumber real property\n"
            "  • Act on any other matter beyond the surplus claim\n\n"
            "DURATION\n"
            "This Limited Power of Attorney shall be effective from the date of "
            "signing and shall terminate upon the earlier of: (a) full disbursement "
            "of surplus funds; (b) written revocation by Principal; or (c) 24 months "
            "from the date of signing.\n\n"
            "PRINCIPAL'S SIGNATURE — MUST BE NOTARIZED\n\n"
            "_____________________________\n"
            "{{full_name}} (Principal)\n"
            "Date: {{signature_date}}\n"
            "Address: {{address}}\n\n"
            "NOTARIZATION\n"
            "STATE OF {{state}}, COUNTY OF {{county}}\n\n"
            "On this day personally appeared {{full_name}}, who is personally known "
            "to me or proved identification, and acknowledged executing this instrument.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "My commission expires: {{notary_expiry}}\n\n"
            "[NOTARY SEAL]\n\n"
            "NON-ATTORNEY NOTICE: {{company_name}} is NOT a law firm. "
            "Consult an attorney if you have questions about this document."
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Purchase Agreement (Surplus Rights)",
        "description": "Outright purchase agreement for the former owner's right to claim surplus proceeds.",
        "category": "agreement",
        "content": (
            "PURCHASE AGREEMENT — SURPLUS FUND RIGHTS\n\n"
            "This Purchase Agreement (\"Agreement\") is entered into as of {{date}} "
            "between {{full_name}} (\"Seller\") and {{company_name}} (\"Buyer\").\n\n"
            "SUBJECT PROPERTY / SURPLUS CLAIM\n"
            "Property: {{property_description}}\n"
            "Parcel / Folio: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "County: {{county}}, State: {{state}}\n"
            "Estimated Surplus on Deposit: {{estimated_surplus}}\n\n"
            "PURCHASE\n"
            "Seller agrees to sell, and Buyer agrees to purchase, all of Seller's right, "
            "title, and interest in and to the surplus fund claim described above "
            "(\"Claim\") for the purchase price of:\n\n"
            "  Purchase Price: $___________\n"
            "  (Representing approximately {{client_percentage}} of the estimated surplus)\n\n"
            "PAYMENT TERMS\n"
            "  [ ] Lump sum due within ___ days of this Agreement\n"
            "  [ ] Deferred — paid from recovered funds within 10 days of disbursement\n"
            "  [ ] Installments: $_______ / month starting ___________\n\n"
            "TRANSFER OF RIGHTS\n"
            "Upon payment in full, Seller transfers all rights to the Claim to Buyer, "
            "including the right to file, pursue, receive, and retain all surplus proceeds. "
            "Seller waives all further claim to the surplus funds after payment.\n\n"
            "REPRESENTATIONS BY SELLER\n"
            "Seller represents that: (a) Seller is the lawful claimant to the surplus; "
            "(b) no other person or entity has a superior claim; (c) the Claim has not "
            "been previously sold or assigned; (d) there are no known liens on the surplus.\n\n"
            "DEFAULT\n"
            "If Buyer fails to make payment when due, this Agreement is voidable at "
            "Seller's election, and all rights revert to Seller.\n\n"
            "NON-ATTORNEY NOTICE: Both parties are encouraged to seek independent "
            "legal counsel before executing this Agreement. {{company_name}} is NOT "
            "a law firm.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Seller)\t\t\t{{assigned_to}} (Buyer / Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Purchase and Sale Agreement",
        "description": "Comprehensive purchase and sale agreement for surplus fund rights including closing terms.",
        "category": "agreement",
        "content": (
            "PURCHASE AND SALE AGREEMENT\n"
            "Surplus Fund Rights\n\n"
            "Date of Agreement: {{date}}\n\n"
            "PARTIES\n"
            "Seller:  {{full_name}}\n"
            "         {{address}}\n"
            "         Phone: {{phone}} | Email: {{email}}\n\n"
            "Buyer:   {{company_name}}\n"
            "         {{company_address}}\n"
            "         Phone: {{company_phone}} | Email: {{company_email}}\n\n"
            "SURPLUS FUND CLAIM\n"
            "Property Address/Description: {{property_description}}\n"
            "Parcel / Folio Number: {{parcel_folio}}\n"
            "Tax Deed Number: {{tax_deed_number}}\n"
            "County: {{county}} | State: {{state}}\n"
            "Claimed Surplus Amount: {{estimated_surplus}}\n\n"
            "TERMS OF PURCHASE\n"
            "1. PURCHASE PRICE\n"
            "   Buyer agrees to pay Seller $__________ (\"Purchase Price\") for all of "
            "   Seller's rights to the surplus fund claim described above.\n\n"
            "2. CLOSING\n"
            "   Closing shall occur on or before ___________.\n"
            "   At closing, Seller shall deliver:\n"
            "   (a) Executed Assignment of Rights\n"
            "   (b) Limited Power of Attorney\n"
            "   (c) Government-issued photo ID copy\n"
            "   (d) Any county-required claim forms\n\n"
            "3. PAYMENT AT CLOSING\n"
            "   [ ] Wire transfer  [ ] Certified check  [ ] Deferred from recovered funds\n"
            "   Escrow Agent (if applicable): ___________\n\n"
            "4. TITLE AND LIENS\n"
            "   Seller warrants that the Claim is free and clear of all competing claims, "
            "   liens, encumbrances, and prior assignments, except as disclosed in writing.\n\n"
            "5. RISK DISCLOSURE\n"
            "   Buyer acknowledges that recovery of the full surplus amount is not guaranteed "
            "   and is subject to county procedures, competing claims, and applicable law.\n\n"
            "6. COOPERATION\n"
            "   Seller agrees to cooperate fully with Buyer's recovery efforts, including "
            "   signing additional documents, providing identification, and responding to "
            "   county inquiries within 5 business days of request.\n\n"
            "7. GOVERNING LAW\n"
            "   This Agreement is governed by the laws of the State of {{state}}.\n\n"
            "NON-ATTORNEY DISCLOSURE\n"
            "{{company_name}} is NOT a law firm. This document was prepared for document "
            "preparation purposes only and does not constitute legal advice. Both parties "
            "should consult independent legal counsel before signing.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Seller)\t\t\t{{assigned_to}} (Buyer)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "Witness: _____________________________\n"
            "Notarized: [ ] Yes  [ ] Not required in this jurisdiction"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Quitclaim Deed",
        "description": "Quitclaim deed transferring any remaining property or surplus interest from former owner.",
        "category": "form",
        "content": (
            "QUITCLAIM DEED\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "THIS QUITCLAIM DEED, executed this {{date}}, by {{full_name}}, "
            "whose mailing address is {{address}} (hereinafter \"Grantor\"), to "
            "{{company_name}}, whose mailing address is {{company_address}} "
            "(hereinafter \"Grantee\"):\n\n"
            "WITNESSETH: That said Grantor, for and in consideration of the sum of "
            "TEN AND NO/100 DOLLARS ($10.00) and other good and valuable consideration "
            "to Grantor in hand paid by Grantee, the receipt whereof is hereby "
            "acknowledged, hereby remises, releases and quitclaims unto the Grantee "
            "forever, all the right, title, interest, claim and demand which the "
            "Grantor has in and to the following described lot or parcel of land, "
            "and/or any associated surplus, excess proceeds, or monetary claims, "
            "situate in {{county}} County, {{state}}:\n\n"
            "LEGAL DESCRIPTION\n"
            "{{property_description}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n\n"
            "INCLUDING but not limited to any right to claim, receive, or recover "
            "tax deed surplus funds / excess proceeds held by the {{county}} Clerk "
            "of Court in the estimated amount of {{estimated_surplus}}.\n\n"
            "TO HAVE AND TO HOLD the same, together with all and singular the "
            "appurtenances thereunto belonging or in anywise appertaining, and all "
            "the estate, right, title, interest, lien, equity and claim whatsoever "
            "of Grantor, either in law or equity, for the use, benefit, and "
            "profit of the said Grantee forever.\n\n"
            "IN WITNESS WHEREOF, Grantor has hereunto set Grantor's hand and seal "
            "the day and year first above written.\n\n"
            "Signed, sealed and delivered in the presence of:\n\n"
            "_____________________________\t\t_____________________________\n"
            "Witness 1 Signature\t\t\t{{full_name}} (Grantor)\n"
            "Printed: ___________________\t\tDate: {{signature_date}}\n\n"
            "_____________________________\n"
            "Witness 2 Signature\n"
            "Printed: ___________________\n\n"
            "STATE OF {{state}}, COUNTY OF {{county}}\n\n"
            "The foregoing instrument was acknowledged before me this {{signature_date}} "
            "by {{full_name}}, who is personally known to me or produced "
            "________________________ as identification.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "My Commission Expires: {{notary_expiry}}\n\n"
            "[NOTARY SEAL]\n\n"
            "IMPORTANT: This Quitclaim Deed should be reviewed by a licensed attorney "
            "before recording. {{company_name}} is NOT a law firm."
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Pre-Estate Agreement",
        "description": "Agreement with heirs or estate representatives for surplus fund recovery before probate completion.",
        "category": "agreement",
        "content": (
            "PRE-ESTATE AGREEMENT\n"
            "Surplus Fund Recovery — Estate / Heir Representation\n\n"
            "This Pre-Estate Agreement (\"Agreement\") is entered into as of {{date}} "
            "between {{full_name}} (\"Heir / Representative,\" also \"Client\") and "
            "{{company_name}} (\"Recovery Company\").\n\n"
            "RECITALS\n"
            "The former property owner (\"Decedent\") held an interest in tax deed "
            "surplus funds prior to death. Client claims to be an heir, beneficiary, "
            "or authorized representative of the Decedent's estate, and wishes to "
            "recover the following surplus funds:\n\n"
            "Property: {{property_description}}\n"
            "Parcel / Folio: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "County: {{county}}, State: {{state}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "ACKNOWLEDGMENT OF PRE-ESTATE STATUS\n"
            "Client acknowledges that:\n"
            "  (a) Probate or estate administration may be required before the county "
            "      will release surplus funds\n"
            "  (b) This Agreement does not substitute for proper estate proceedings\n"
            "  (c) Recovery Company is NOT a law firm and cannot provide estate or "
            "      probate legal services\n"
            "  (d) An attorney referral will be provided if probate is required\n\n"
            "SERVICES\n"
            "Recovery Company will:\n"
            "  • Research the surplus fund claim and county filing requirements\n"
            "  • Assist Client in gathering required documentation\n"
            "  • Coordinate the claim filing once Client establishes legal authority\n"
            "  • Refer Client to a probate attorney if required (at Client's cost)\n\n"
            "FEE AGREEMENT\n"
            "Company retains {{fee_percentage}} of all recovered surplus funds as its "
            "contingency fee. Client (or estate) receives {{client_percentage}}. No fee "
            "is charged if no funds are recovered.\n\n"
            "CLIENT REPRESENTATIONS\n"
            "Client represents that: (a) Client has a legal interest in the surplus "
            "as an heir, beneficiary, or authorized estate representative; (b) Client "
            "has disclosed all known heirs and competing claimants; (c) no other party "
            "has been retained for this specific claim.\n\n"
            "GOVERNING LAW: {{state}}\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Heir / Representative)\t{{assigned_to}} (Recovery Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "Relationship to Decedent: ___________\n"
            "Case No.: {{case_number}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}}\n"
            "NOT A LAW FIRM — Document Preparation Services Only"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Notary Affidavit (Surplus Claim)",
        "description": "Notarized affidavit affirming identity and ownership for a tax deed surplus fund claim submission.",
        "category": "form",
        "content": (
            "AFFIDAVIT OF IDENTITY AND OWNERSHIP\n"
            "Tax Deed Surplus Fund Claim\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "BEFORE ME, the undersigned authority, personally appeared {{full_name}} "
            "(\"Affiant\"), who, being first duly sworn, deposes and states:\n\n"
            "1. IDENTITY\n"
            "   My full legal name is {{full_name}}. I reside at {{address}}. "
            "   My telephone number is {{phone}}. My email address is {{email}}.\n\n"
            "2. FORMER OWNERSHIP\n"
            "   I was the owner of record of the following real property at the time "
            "   of the tax deed sale:\n"
            "   Property: {{property_description}}\n"
            "   Parcel / Folio No.: {{parcel_folio}}\n"
            "   Tax Deed No.: {{tax_deed_number}}\n"
            "   County: {{county}}, State: {{state}}\n\n"
            "3. SURPLUS FUND CLAIM\n"
            "   I am entitled to claim the tax deed surplus / excess proceeds resulting "
            "   from the above tax deed sale, estimated at {{estimated_surplus}}, "
            "   currently held by the Clerk of Court, {{county}} County, {{state}}.\n\n"
            "4. NO PRIOR CLAIM OR ASSIGNMENT\n"
            "   I have not previously filed a claim for these surplus funds, nor have "
            "   I assigned or transferred my rights to these funds to any other party, "
            "   except as disclosed in writing to {{company_name}}.\n\n"
            "5. NO KNOWN COMPETING CLAIMS\n"
            "   To the best of my knowledge, there are no other parties with a superior "
            "   legal right to these surplus funds, except as I have disclosed.\n\n"
            "6. AUTHORIZATION\n"
            "   I hereby authorize {{company_name}} to submit this affidavit and any "
            "   accompanying claim documents to the {{county}} Clerk of Court on my behalf.\n\n"
            "I declare under penalty of perjury that the foregoing is true and correct "
            "to the best of my knowledge.\n\n"
            "_____________________________\n"
            "{{full_name}} (Affiant)\n"
            "Date: {{signature_date}}\n\n"
            "SWORN TO AND SUBSCRIBED before me this {{signature_date}}.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "State of {{state}}\n"
            "Commission No.: {{notary_commission}}\n"
            "My Commission Expires: {{notary_expiry}}\n\n"
            "[NOTARY SEAL]\n\n"
            "Prepared by: {{company_name}} — Document Preparation Services Only\n"
            "NOT LEGAL ADVICE | {{company_phone}} | {{company_email}}"
        ),
    },
    # ── OVERAGES — original templates ─────────────────────────────────────────
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Overage Case Status Report",
        "description": "Periodic status report for a tax overage recovery case sent to the former owner.",
        "category": "report",
        "content": (
            "CASE STATUS REPORT — TAX OVERAGE RECOVERY\n"
            "{{company_name}}\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "County: {{county}}\n"
            "Report Date: {{date}}\n"
            "Recovery Specialist: {{assigned_to}}\n\n"
            "PROPERTY SUMMARY\n"
            "Parcel / Folio: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "CURRENT WORKFLOW STEP\n"
            "Status: ___________\n"
            "Claim Filed:  [ ] Yes (date: _________)  [ ] Pending  [ ] No\n"
            "County Response Received:  [ ] Yes  [ ] Pending  [ ] No\n\n"
            "RECENT ACTIVITY\n"
            "{{notes}}\n\n"
            "NEXT STEPS\n"
            "1. ___________\n"
            "2. ___________\n\n"
            "IMPORTANT: {{company_name}} is not a law firm and does not provide legal "
            "advice. If competing claimants or legal complexities arise, an attorney "
            "referral will be recommended.\n\n"
            "Questions? {{company_phone}} | {{company_email}}\n\n"
            "{{company_name}}\n{{company_address}}"
        ),
    },
    # ── OVERAGES — additional source-document templates ────────────────────────
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Fee Agreement (with Cost Cap)",
        "description": "Contingency fee agreement for surplus recovery with a capped cost advance provision.",
        "category": "agreement",
        "content": (
            "FEE AGREEMENT — SURPLUS RECOVERY SERVICES\n"
            "{{company_name}}\n\n"
            "Date: {{date}}\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n\n"
            "PROPERTY / CLAIM INFORMATION\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "CONTINGENCY FEE\n"
            "Client agrees to pay {{company_name}} a contingency fee equal to "
            "{{fee_percentage}} of all surplus funds successfully recovered. "
            "Client's net share shall be {{client_percentage}} of funds recovered. "
            "No fee is owed if no funds are recovered.\n\n"
            "COST ADVANCE CAP\n"
            "{{company_name}} may advance reasonable out-of-pocket costs (filing fees, "
            "recording fees, notary fees, and similar administrative costs) up to a "
            "maximum of {{cost_cap}} on behalf of Client. These advances shall be "
            "reimbursed to {{company_name}} from recovered funds prior to disbursement "
            "of Client's share. Client shall not be required to pay costs in excess of "
            "the {{cost_cap}} cap even if actual costs exceed that amount.\n\n"
            "SCOPE OF SERVICES\n"
            "Services include: researching the claim; preparing and submitting claim "
            "documentation to the applicable county authority; coordinating follow-up "
            "until funds are released; and disbursing proceeds per this Agreement.\n\n"
            "NOT A LAW FIRM\n"
            "{{company_name}} is NOT a law firm and does not provide legal advice. "
            "Client is encouraged to consult a licensed attorney. If legal proceedings "
            "are required, attorney fees shall be separate from this Agreement.\n\n"
            "TERM & TERMINATION\n"
            "This Agreement is effective upon signing and remains in effect until the "
            "claim is resolved, funds are disbursed, the claim is formally denied, or "
            "either party provides written notice of termination.\n\n"
            "By signing below, Client acknowledges reading and understanding this "
            "Agreement in its entirety.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} ({{company_name}})\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Assignment of Rights (Full — Individual)",
        "description": "Full irrevocable assignment of all surplus fund rights from an individual former owner.",
        "category": "agreement",
        "content": (
            "ASSIGNMENT OF RIGHTS TO SURPLUS FUNDS\n"
            "(FULL ASSIGNMENT — INDIVIDUAL)\n\n"
            "This Assignment of Rights (\"Assignment\") is made and entered into as of "
            "{{date}}, by and between {{full_name}}, whose address is {{address}} "
            "(\"Assignor\"), and {{company_name}}, whose address is {{company_address}} "
            "(\"Assignee\").\n\n"
            "RECITALS\n"
            "WHEREAS, Assignor was the former owner of record of the real property "
            "described as:\n"
            "  Property / Legal Description: {{property_description}}\n"
            "  Parcel / Folio No.: {{parcel_folio}}\n"
            "  County: {{county}}, State: {{state}}\n"
            "  Tax Deed No.: {{tax_deed_number}} — {{tax_deed_year}}\n\n"
            "WHEREAS, the above property was sold at a tax deed sale resulting in "
            "surplus / excess proceeds (\"Surplus Funds\") in the estimated amount of "
            "{{estimated_surplus}}, currently held by the {{county}} Clerk of Courts "
            "or applicable governmental authority;\n\n"
            "NOW, THEREFORE, in consideration of the mutual covenants herein and other "
            "good and valuable consideration, the parties agree as follows:\n\n"
            "1. FULL ASSIGNMENT\n"
            "Assignor hereby irrevocably assigns, transfers, sets over, and conveys to "
            "Assignee ALL of Assignor's right, title, and interest in and to the "
            "Surplus Funds, including without limitation: (a) the right to file and "
            "prosecute a claim; (b) the right to receive payment; (c) the right to "
            "execute any and all documents required by the county or court; and (d) "
            "the right to institute legal proceedings if necessary to recover the "
            "Surplus Funds.\n\n"
            "2. COMPENSATION\n"
            "As full consideration for this Assignment, Assignee shall remit to "
            "Assignor {{client_percentage}} of all Surplus Funds actually recovered, "
            "net of documented recovery costs, within ten (10) business days of "
            "receipt. Assignee shall retain {{fee_percentage}} as its recovery fee.\n\n"
            "3. REPRESENTATIONS & WARRANTIES\n"
            "Assignor represents and warrants that: (a) Assignor is the lawful owner "
            "of the claim; (b) Assignor has full authority to execute this Assignment; "
            "(c) Assignor has not previously assigned, pledged, or encumbered these "
            "rights to any other party; (d) Assignor is not aware of any competing "
            "claims, lien holders, or legal holds on the Surplus Funds except as "
            "disclosed to Assignee in writing.\n\n"
            "4. INDEMNIFICATION\n"
            "Assignor agrees to indemnify and hold harmless Assignee from any claims "
            "by third parties asserting rights to the Surplus Funds arising from facts "
            "known to Assignor at the time of this Assignment.\n\n"
            "5. NON-ATTORNEY DISCLOSURE\n"
            "{{company_name}} is NOT a law firm and none of its representatives are "
            "licensed attorneys. Nothing herein constitutes legal advice. Assignor "
            "is strongly encouraged to consult a licensed attorney prior to signing.\n\n"
            "6. GOVERNING LAW\n"
            "This Assignment shall be governed by the laws of the State of {{state}}.\n\n"
            "IN WITNESS WHEREOF, the parties have executed this Assignment as of the "
            "date first written above.\n\n"
            "ASSIGNOR:\n"
            "_____________________________\n"
            "{{full_name}}\n"
            "Date: {{signature_date}}\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "Personally appeared the above-named {{full_name}}, known to me (or "
            "satisfactorily proven), who executed the foregoing Assignment and "
            "acknowledged it to be his/her free act and deed.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "My Commission Expires: {{notary_expiry}}\n"
            "[NOTARY SEAL]\n\n"
            "ASSIGNEE:\n"
            "_____________________________\n"
            "{{assigned_to}}, Authorized Representative\n"
            "{{company_name}}\n"
            "Date: {{signature_date}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Assignment of Rights (Partial — Individual, Not Notarized)",
        "description": "Partial assignment of surplus fund rights from an individual — no notarization required.",
        "category": "agreement",
        "content": (
            "PARTIAL ASSIGNMENT OF RIGHTS TO SURPLUS FUNDS\n"
            "(INDIVIDUAL — NOT NOTARIZED)\n\n"
            "Date: {{date}}\n"
            "Case No.: {{case_number}}\n\n"
            "PARTIES\n"
            "Assignor: {{full_name}}, {{address}}\n"
            "Assignee: {{company_name}}, {{company_address}}\n\n"
            "PROPERTY INFORMATION\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "PARTIAL ASSIGNMENT\n"
            "For good and valuable consideration, Assignor hereby assigns and "
            "transfers to Assignee a partial interest in and to the surplus funds "
            "produced by the above-referenced tax deed sale, specifically:\n"
            "  Assignee's Share: {{fee_percentage}} of all funds recovered\n"
            "  Assignor's Share: {{client_percentage}} of all funds recovered\n\n"
            "Assignee is authorized to file the claim, communicate with county "
            "officials, and receive the full amount of surplus funds on behalf of "
            "both parties, with Assignor's share to be remitted within ten (10) "
            "business days of receipt.\n\n"
            "REPRESENTATIONS\n"
            "Assignor certifies that: (a) Assignor has authority to assign these "
            "rights; (b) no prior assignment has been made; (c) no competing claims "
            "are known except as disclosed.\n\n"
            "NON-ATTORNEY NOTICE\n"
            "{{company_name}} is NOT a law firm. Assignor is encouraged to seek "
            "independent legal counsel before signing.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Assignor)\t\t\t{{assigned_to}} (Assignee)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Assignment of Rights (Partial — Entity)",
        "description": "Partial assignment of surplus fund rights from a corporate or trust entity.",
        "category": "agreement",
        "content": (
            "PARTIAL ASSIGNMENT OF RIGHTS TO SURPLUS FUNDS\n"
            "(ENTITY ASSIGNOR)\n\n"
            "Date: {{date}}\n"
            "Case No.: {{case_number}}\n\n"
            "PARTIES\n"
            "Assignor: {{entity_name}}, a {{state}} entity\n"
            "  Authorized Signatory: {{signor_name}}, {{signor_title}}\n"
            "  Address: {{address}}\n"
            "Assignee: {{company_name}}, {{company_address}}\n\n"
            "PROPERTY INFORMATION\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "PARTIAL ASSIGNMENT\n"
            "For good and valuable consideration, Assignor (acting through its duly "
            "authorized representative identified above) hereby assigns and transfers "
            "to Assignee a partial interest in and to the surplus funds produced by "
            "the above-referenced tax deed sale:\n"
            "  Assignee's Share: {{fee_percentage}} of all funds recovered\n"
            "  Assignor's Share: {{client_percentage}} of all funds recovered\n\n"
            "Assignee is authorized to file the claim, communicate with the county "
            "clerk, tax collector, and other governmental bodies, and receive the "
            "full amount of surplus funds on behalf of all parties, with Assignor's "
            "share remitted within ten (10) business days of receipt.\n\n"
            "AUTHORITY OF SIGNATORY\n"
            "{{signor_name}} represents that he/she is duly authorized to execute "
            "this Assignment on behalf of {{entity_name}} and that the entity has "
            "full power and authority to assign these rights.\n\n"
            "REPRESENTATIONS\n"
            "Assignor certifies: (a) Assignor holds valid title to the claim; "
            "(b) no prior assignment has been made; (c) no competing claims are "
            "known except as disclosed in writing to Assignee.\n\n"
            "NON-ATTORNEY NOTICE\n"
            "{{company_name}} is NOT a law firm. Assignor is encouraged to consult "
            "a licensed attorney before signing.\n\n"
            "ASSIGNOR — {{entity_name}}\n"
            "By: _____________________________\n"
            "Name: {{signor_name}}\n"
            "Title: {{signor_title}}\n"
            "Date: {{signature_date}}\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "Personally appeared {{signor_name}}, as {{signor_title}} of "
            "{{entity_name}}, who acknowledged executing this Assignment on behalf "
            "of the entity.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "My Commission Expires: {{notary_expiry}}\n"
            "[NOTARY SEAL]\n\n"
            "ASSIGNEE:\n"
            "_____________________________\n"
            "{{assigned_to}}, {{company_name}}\n"
            "Date: {{signature_date}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "County Tax Sale Overage Claim Form",
        "description": "Sworn claim form submitted to the county to recover tax sale surplus funds — adaptable to any county.",
        "category": "form",
        "content": (
            "CLAIM FOR TAX SALE OVERAGE\n"
            "{{county}}, State of {{state}}\n\n"
            "MAP REFERENCE / PARCEL NO.: {{parcel_folio}}\n"
            "YEAR OF SALE: {{tax_deed_year}}\n"
            "PHYSICAL LOCATION OF PROPERTY: {{property_description}}\n"
            "NAME OF DEFAULTING TAXPAYER(S): {{defendant_name}}\n"
            "NAME OF OWNER(S) AT END OF REDEMPTION PERIOD: {{full_name}}\n"
            "MAILING ADDRESS OF OWNER(S) CLAIMING OVERBID: {{address}}\n"
            "NAME AND ADDRESS OF ANY MORTGAGE OR LIEN HOLDER(S): "
            "_______________________________________________\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "PERSONALLY appeared the undersigned, who being sworn, says that this "
            "claim is pursuant to applicable state law for the overage produced by a "
            "delinquent tax sale. The tax sale is described in the deed from the Tax "
            "Collector to the highest bidder, recorded in Deed Book _____, Page _____, "
            "Register of Deeds Office for {{county}}, a copy of which is attached to "
            "this claim. The amount over the full amount due in taxes, assessments, "
            "penalties and costs, produced by the tax sale as shown by the Tax "
            "Collector is the amount lawfully owing to the undersigned.\n\n"
            "A copy of the deed or probate conveyance sheet showing ownership in the "
            "undersigned is attached to verify to whom the refund check should be made "
            "payable. The undersigned has been authorized to receive the refund check "
            "on behalf of all. The undersigned indemnifies and holds {{county}}, its "
            "agents and employees harmless against claims by any other persons for "
            "such overage and waives all causes of action against the County, its "
            "agents or employees, arising out of the tax sale. The undersigned "
            "attaches a copy of the Social Security card and such other identification "
            "as the Tax Collector shall request.\n\n"
            "Signature: ___________________________ Name (Printed): {{full_name}}\n\n"
            "SWORN to before me this _______ day of _______________, 20______.\n\n"
            "_____________________________  (L.S.)\n"
            "{{notary_name}}, Notary Public for the State of {{state}}\n"
            "My Commission Expires: {{notary_expiry}}\n\n"
            "*** FOR COUNTY USE ONLY ***\n"
            "I verify the amount of overage (cash produced in excess of full taxes, "
            "assessments, penalties and costs) as $_______________. This overage is "
            "payable to the owner of record immediately before the end of the "
            "redemption period. I verify all required documents were received.\n\n"
            "Signed: ___________________________ Date: _____________\n"
            "  Delinquent Tax Collector Division\n"
            "Approved By: _______________________ Date: _____________\n"
            "  County Tax Collector / Agent\n\n"
            "RETURNED ON: ___________________ ID: ___________________\n\n"
            "Prepared with assistance by: {{company_name}} | {{company_phone}} | {{company_email}}\n"
            "Document Preparation Only — NOT Legal Advice"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "County Overage Claim — Filing Instructions",
        "description": "Step-by-step instructions for filing a county tax sale overage claim.",
        "category": "letter",
        "content": (
            "INSTRUCTIONS FOR FILING YOUR TAX SALE OVERAGE CLAIM\n"
            "Prepared by: {{company_name}} | {{company_phone}}\n\n"
            "Client: {{full_name}} | Case No.: {{case_number}}\n"
            "County: {{county}}, {{state}} | Parcel: {{parcel_folio}}\n\n"
            "IMPORTANT: Per state law, the OWNER OF RECORD IMMEDIATELY BEFORE THE "
            "END OF THE REDEMPTION PERIOD OF THE TAX SALE is the legal claimant "
            "of the overage. The redemption period typically ends twelve (12) months "
            "after the tax sale date.\n\n"
            "DOCUMENTS REQUIRED FOR SUBMISSION:\n"
            "  1. Completed and notarized Claim for Tax Sale Overage form\n"
            "  2. Copy of the tax deed (from Tax Collector to highest bidder)\n"
            "  3. Copy of the deed or probate conveyance sheet showing your ownership\n"
            "  4. Copy of your government-issued photo ID\n"
            "  5. Copy of your Social Security card\n"
            "  6. If claiming through Power of Attorney: copy of the executed POA, "
            "plus POA holder's photo ID and Social Security card or FEIN\n\n"
            "CLAIM FORM COMPLETION CHECKLIST:\n"
            "  [ ] Map Reference / Parcel Number of the property\n"
            "  [ ] Tax Sale Year and Item Number\n"
            "  [ ] Physical location / address of the property\n"
            "  [ ] Name of Defaulting Taxpayer\n"
            "  [ ] Your name and mailing address as owner at end of redemption period\n"
            "  [ ] Name and address of any mortgage or lien holders (write NONE if none)\n"
            "  [ ] Deed Book and Page Number of the Tax Deed\n"
            "  [ ] Signed BEFORE a Notary Public\n\n"
            "IMPORTANT NOTES:\n"
            "  • Funds are not released until at least 90 days after the tax deed is "
            "recorded, to allow for competing claimant objections.\n"
            "  • If the County questions your claim, they may require a court order "
            "before releasing funds.\n"
            "  • {{company_name}} will coordinate submission and follow-up on your "
            "behalf per your signed Contingency Agreement.\n\n"
            "Questions? Contact us at {{company_phone}} | {{company_email}}\n"
            "{{company_name}} | {{company_address}}\n"
            "Document Preparation Services Only — NOT Legal Advice"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Power of Attorney (Standard — Outside PA/GA)",
        "description": "36-month limited power of attorney authorizing surplus fund recovery — for use outside Pennsylvania and Georgia.",
        "category": "agreement",
        "content": (
            "LIMITED POWER OF ATTORNEY\n"
            "(SURPLUS FUND RECOVERY — STANDARD 36-MONTH)\n\n"
            "KNOW ALL PERSONS BY THESE PRESENTS that I, {{full_name}}, residing at "
            "{{address}} (\"Principal\"), do hereby appoint {{company_name}}, and its "
            "authorized agents and representatives, as my true and lawful "
            "Attorney-in-Fact (\"Agent\") for the limited purposes set forth below.\n\n"
            "PROPERTY SUBJECT TO THIS POA\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "GRANT OF AUTHORITY\n"
            "Agent is hereby authorized, on behalf of Principal, to:\n"
            "  1. Prepare, execute, and file all documents necessary to claim the "
            "tax deed surplus funds referenced above from the {{county}} Clerk of "
            "Court or other applicable authority;\n"
            "  2. Communicate with and provide information to the county clerk, tax "
            "collector, court clerk, and any other governmental office regarding "
            "this specific surplus claim;\n"
            "  3. Endorse and negotiate checks payable to Principal for surplus "
            "funds, solely for the purpose of disbursement per the parties' written "
            "Fee Agreement;\n"
            "  4. Execute any affidavits, certifications, or supplemental documents "
            "required by the county or court in connection with this claim.\n\n"
            "LIMITATIONS\n"
            "This Power of Attorney is LIMITED solely to the recovery of surplus "
            "funds from the above-described property. Agent may NOT: (a) bind "
            "Principal to any obligation other than as stated herein; (b) appear in "
            "court on Principal's behalf in an adversarial proceeding; or (c) provide "
            "legal advice to Principal.\n\n"
            "TERM\n"
            "This Power of Attorney shall remain in effect for thirty-six (36) months "
            "from the date of execution, or until the surplus funds are disbursed or "
            "the claim is formally closed, whichever occurs first.\n\n"
            "THIRD-PARTY RELIANCE\n"
            "Any third party may rely on a copy of this Power of Attorney as though "
            "it were an original.\n\n"
            "NON-ATTORNEY DISCLOSURE\n"
            "{{company_name}} is NOT a law firm and does not provide legal advice. "
            "Principal is encouraged to consult a licensed attorney before signing.\n\n"
            "Executed this {{date}}.\n\n"
            "_____________________________\n"
            "{{full_name}} (Principal)\n\n"
            "STATE OF {{state}}\n"
            "COUNTY OF {{county}}\n\n"
            "Personally appeared {{full_name}}, who being known to me (or "
            "satisfactorily proven), acknowledged the foregoing instrument to be "
            "his/her free act and deed.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "My Commission Expires: {{notary_expiry}}\n"
            "[NOTARY SEAL]"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Pre-Estate Agreement",
        "description": "Agreement with an heir-in-waiting to recover surplus funds from an estate with a pending escheat date.",
        "category": "agreement",
        "content": (
            "PRE-ESTATE SURPLUS RECOVERY AGREEMENT\n\n"
            "This Pre-Estate Agreement (\"Agreement\") is entered into as of {{date}} "
            "by and between {{full_name}} (\"Client\"), heir/interested party to the "
            "estate of {{deceased_name}} (deceased {{deceased_date}}), and "
            "{{company_name}} (\"Recovery Company\").\n\n"
            "ESTATE & PROPERTY INFORMATION\n"
            "Decedent: {{deceased_name}}\n"
            "Date of Death: {{deceased_date}}\n"
            "Client's Relationship to Decedent: {{heir_relationship}}\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n"
            "Escheat Date (Funds revert to State): {{escheat_date}}\n\n"
            "BACKGROUND\n"
            "The above-described property was sold at a tax deed sale. The resulting "
            "surplus funds are currently held by the {{county}} Clerk of Court and "
            "are claimable by the estate of the former owner. These funds will "
            "escheat (revert) to the State of {{state}} if not claimed before "
            "{{escheat_date}}.\n\n"
            "SCOPE OF SERVICES\n"
            "Recovery Company agrees to assist Client in:\n"
            "  1. Documenting Client's interest in the estate and right to claim;\n"
            "  2. Coordinating with the Probate Court or estate administrator as needed;\n"
            "  3. Preparing and submitting the surplus fund claim on behalf of the estate;\n"
            "  4. Following up with the county until funds are released.\n\n"
            "CONTINGENCY FEE\n"
            "Client agrees to pay Recovery Company {{fee_percentage}} of all surplus "
            "funds actually recovered. Client's net share shall be {{client_percentage}}. "
            "No fee is owed if no funds are recovered.\n\n"
            "PROBATE REQUIREMENT\n"
            "If the county requires letters testamentary, letters of administration, "
            "or other probate documentation before releasing funds, Client agrees to "
            "cooperate fully in obtaining such documents. Probate court fees, if any, "
            "are the responsibility of Client or the estate and are not included in "
            "this Agreement.\n\n"
            "NOT A LAW FIRM\n"
            "{{company_name}} is NOT a law firm. If probate or legal proceedings are "
            "required, an attorney referral will be recommended. Attorney fees are "
            "separate from and not covered by this Agreement.\n\n"
            "ESCHEAT URGENCY\n"
            "Client acknowledges that time is of the essence due to the escheat date "
            "of {{escheat_date}} and agrees to provide all requested documentation "
            "promptly.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} (Recovery Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Inheritance Expectancy Agreement (Full Irrevocable)",
        "description": "Full irrevocable assignment of inheritance expectancy interest in estate surplus funds.",
        "category": "agreement",
        "content": (
            "INHERITANCE EXPECTANCY AGREEMENT\n"
            "(FULL IRREVOCABLE ASSIGNMENT)\n\n"
            "This Inheritance Expectancy Agreement (\"Agreement\") is entered into as "
            "of {{date}} by and between {{full_name}} (\"Assignor\") and "
            "{{company_name}} (\"Assignee\").\n\n"
            "RECITALS\n"
            "Assignor is an heir or interested party to the estate of {{deceased_name}}, "
            "deceased, and has a legitimate expectancy interest in surplus funds "
            "generated from the tax deed sale of the following property:\n"
            "  County: {{county}}, State: {{state}}\n"
            "  Parcel / Folio No.: {{parcel_folio}}\n"
            "  Tax Deed No.: {{tax_deed_number}}\n"
            "  Estimated Surplus: {{estimated_surplus}}\n"
            "  Assignor's Relationship to Decedent: {{heir_relationship}}\n\n"
            "FULL IRREVOCABLE ASSIGNMENT\n"
            "In consideration of Assignee's recovery services and other valuable "
            "consideration, Assignor hereby irrevocably assigns to Assignee ALL of "
            "Assignor's expectancy interest in and right to receive surplus funds from "
            "the above-referenced estate and tax deed sale, including the right to "
            "file claims, receive payment, and execute all necessary documents.\n\n"
            "COMPENSATION\n"
            "Assignee shall remit to Assignor {{client_percentage}} of all surplus "
            "funds actually recovered on Assignor's behalf, within ten (10) business "
            "days of receipt. Assignee retains {{fee_percentage}} as its recovery fee.\n\n"
            "IRREVOCABILITY\n"
            "This Assignment is irrevocable and shall survive the death or incapacity "
            "of either party, binding their respective heirs, successors, and assigns.\n\n"
            "NOT A LAW FIRM\n"
            "{{company_name}} is NOT a law firm. Assignor is encouraged to consult "
            "a licensed attorney or estate planning professional before signing.\n\n"
            "_____________________________\n"
            "{{full_name}} (Assignor)\n"
            "Date: {{signature_date}}\n\n"
            "STATE OF {{state}} | COUNTY OF {{county}}\n\n"
            "Sworn to and subscribed before me this {{date}}.\n\n"
            "_____________________________\n"
            "{{notary_name}}, Notary Public\n"
            "Commission No.: {{notary_commission}}\n"
            "Expires: {{notary_expiry}}\n"
            "[NOTARY SEAL]\n\n"
            "_____________________________\n"
            "{{assigned_to}}, {{company_name}}\n"
            "Date: {{signature_date}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Late Claim Addendum",
        "description": "Addendum addressing claims filed after the initial redemption period — attaches to the primary agreement.",
        "category": "agreement",
        "content": (
            "LATE CLAIM ADDENDUM\n"
            "To: [Primary Agreement / Assignment dated {{date}}]\n\n"
            "Client: {{full_name}}\n"
            "Case No.: {{case_number}}\n"
            "County: {{county}}, State: {{state}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n\n"
            "PURPOSE\n"
            "This Addendum supplements the parties' primary agreement (identified "
            "above) to address the fact that the surplus fund claim referenced therein "
            "is being filed after the initial ninety (90) day period following "
            "recordation of the tax deed.\n\n"
            "ACKNOWLEDGMENT OF LATE FILING\n"
            "Client acknowledges that:\n"
            "  (a) The standard 90-day claim window has passed;\n"
            "  (b) Competing claims may have been filed during that period;\n"
            "  (c) The county or court may require additional documentation or a "
            "court order before releasing funds;\n"
            "  (d) In some jurisdictions, claims filed after the statutory deadline "
            "may be subject to judicial review or may be denied.\n\n"
            "ADDITIONAL SERVICES\n"
            "{{company_name}} agrees to make reasonable efforts to pursue the late "
            "claim, including:\n"
            "  1. Researching the current status of the surplus funds;\n"
            "  2. Submitting documentation to the county demonstrating Client's "
            "entitlement;\n"
            "  3. Coordinating with a licensed attorney if judicial intervention is "
            "required (attorney fees are separate and not covered by the base "
            "contingency agreement).\n\n"
            "FEE ADJUSTMENT\n"
            "The parties agree that the contingency fee stated in the primary "
            "agreement ({{fee_percentage}}) shall remain unchanged. However, if "
            "extraordinary legal costs are required to pursue the late claim, Client "
            "and {{company_name}} will negotiate in good faith before incurring such "
            "costs.\n\n"
            "NO GUARANTEE\n"
            "{{company_name}} makes no guarantee that a late claim will be approved "
            "or that funds will be recovered. This Addendum does not constitute a "
            "promise of recovery.\n\n"
            "By signing below, Client acknowledges and accepts the terms of this "
            "Addendum.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{assigned_to}} ({{company_name}})\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Email: Overages List Request (Standard)",
        "description": "Email to a county tax collector requesting the list of current tax sale surplus funds.",
        "category": "letter",
        "content": (
            "SUBJECT: Request for Tax Sale Surplus / Overage Funds List — {{county}}\n\n"
            "Date: {{date}}\n\n"
            "Dear {{county}} Tax Collector / Delinquent Tax Division,\n\n"
            "My name is {{assigned_to}} and I am a representative of {{company_name}}, "
            "a surplus fund recovery firm located at {{company_address}}.\n\n"
            "We are writing to respectfully request a copy of your current list of "
            "unclaimed tax sale surplus / overage funds. We assist former property "
            "owners in recovering funds they are legally entitled to, and we work "
            "exclusively within the bounds of {{state}} law.\n\n"
            "Specifically, we are requesting:\n"
            "  1. A list of tax deed sales that produced surplus proceeds currently "
            "held by your office or the {{county}} Clerk of Court;\n"
            "  2. For each item: parcel number, former owner name, sale date, sale "
            "amount, surplus amount, and claim deadline (if applicable).\n\n"
            "We understand this information may be a public record under {{state}} "
            "law and the Freedom of Information Act. We are happy to pay any "
            "applicable records request fee.\n\n"
            "Please feel free to contact us at the information below. We appreciate "
            "your time and look forward to working with your office.\n\n"
            "Sincerely,\n\n"
            "{{assigned_to}}\n"
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Email: Mortgage Foreclosure Overages List Request",
        "description": "Email to a county requesting the list of mortgage foreclosure surplus / overbid funds.",
        "category": "letter",
        "content": (
            "SUBJECT: Request for Mortgage Foreclosure Surplus Funds List — {{county}}\n\n"
            "Date: {{date}}\n\n"
            "Dear {{county}} Clerk of Court / Civil Division,\n\n"
            "My name is {{assigned_to}}, representing {{company_name}}, a surplus "
            "fund recovery company assisting former homeowners in reclaiming funds "
            "they are legally entitled to following mortgage foreclosure sales.\n\n"
            "We are writing to request your current list of unclaimed mortgage "
            "foreclosure surplus funds / overbids held by your office. Under "
            "{{state}} law, former homeowners whose properties were sold at "
            "foreclosure auction for more than the amount owed are entitled to "
            "claim the surplus proceeds.\n\n"
            "We respectfully request the following information:\n"
            "  1. Case numbers and property addresses for foreclosure sales that "
            "produced surplus proceeds currently on deposit with the court;\n"
            "  2. Former owner / defendant names and last known addresses;\n"
            "  3. Amount of surplus on deposit and any applicable claim deadline.\n\n"
            "This information is a matter of public record. We are prepared to pay "
            "any applicable copy or records request fees.\n\n"
            "Thank you for your assistance. Please contact us at:\n\n"
            "{{assigned_to}}\n"
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Email: Notice of Claim to Recovery Agency",
        "description": "Formal notice to a county or agency that a client's surplus fund claim has been filed.",
        "category": "letter",
        "content": (
            "SUBJECT: Notice of Surplus Fund Claim — {{parcel_folio}} / {{full_name}}\n\n"
            "Date: {{date}}\n\n"
            "{{county}} Tax Collector / Clerk of Court\n"
            "Attn: Surplus / Overage Division\n\n"
            "RE: Surplus Fund Claim\n"
            "Former Owner: {{full_name}}\n"
            "Parcel / Folio No.: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Estimated Surplus: {{estimated_surplus}}\n\n"
            "Dear Sir / Madam,\n\n"
            "Please be advised that {{company_name}} represents {{full_name}}, the "
            "former owner / legal claimant of the above-referenced tax deed surplus "
            "funds, pursuant to a signed Assignment of Rights and/or Power of "
            "Attorney executed on {{signature_date}}.\n\n"
            "We are hereby providing formal notice that a claim for the surplus "
            "funds referenced above will be (or has been) submitted to your office "
            "on behalf of our client. We request that:\n"
            "  1. All correspondence regarding this claim be directed to us at the "
            "contact information below;\n"
            "  2. No disbursement of the surplus funds be made to any other party "
            "without prior written notice to us;\n"
            "  3. You confirm receipt of this notice and advise us of the current "
            "status and any outstanding requirements.\n\n"
            "Enclosed / attached with this notice:\n"
            "  [ ] Signed Assignment of Rights\n"
            "  [ ] Power of Attorney\n"
            "  [ ] Client government-issued photo ID\n"
            "  [ ] Claim form (completed)\n\n"
            "Thank you for your prompt attention to this matter.\n\n"
            "Respectfully,\n\n"
            "{{assigned_to}}\n"
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Claimant Satisfaction Survey",
        "description": "Post-recovery satisfaction survey sent to clients after surplus funds are disbursed.",
        "category": "form",
        "content": (
            "CLAIMANT SATISFACTION SURVEY\n"
            "{{company_name}}\n\n"
            "Dear {{full_name}},\n\n"
            "Thank you for trusting {{company_name}} to assist with your surplus fund "
            "recovery. We value your feedback and ask that you take a few moments to "
            "complete this brief survey. Your responses help us improve our service.\n\n"
            "Case No.: {{case_number}}\n"
            "County: {{county}} | Parcel: {{parcel_folio}}\n"
            "Recovery Specialist: {{assigned_to}}\n\n"
            "PLEASE RATE THE FOLLOWING (1 = Poor, 5 = Excellent):\n\n"
            "1. Initial contact and explanation of services\n"
            "   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5\n\n"
            "2. Speed and responsiveness of communication\n"
            "   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5\n\n"
            "3. Accuracy and clarity of documents provided\n"
            "   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5\n\n"
            "4. Timeliness of fund disbursement\n"
            "   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5\n\n"
            "5. Overall satisfaction with our service\n"
            "   [ ] 1  [ ] 2  [ ] 3  [ ] 4  [ ] 5\n\n"
            "6. Would you recommend {{company_name}} to family or friends?\n"
            "   [ ] Definitely Yes  [ ] Probably Yes  [ ] Not Sure  [ ] No\n\n"
            "7. How did you first hear about us?\n"
            "   [ ] Mail / Letter  [ ] Internet Search  [ ] Referral  [ ] Other: _________\n\n"
            "8. Additional comments or suggestions:\n"
            "   _______________________________________________________________\n"
            "   _______________________________________________________________\n\n"
            "May we use your experience as a testimonial (name withheld if preferred)?\n"
            "   [ ] Yes, with my name  [ ] Yes, anonymously  [ ] No\n\n"
            "Thank you for your time!\n\n"
            "{{company_name}} | {{company_phone}} | {{company_email}}\n"
            "{{company_address}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Personal Pitch Letter (Former Owner Outreach)",
        "description": "Marketing letter sent to former property owners informing them of unclaimed surplus funds.",
        "category": "letter",
        "content": (
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "Date: {{date}}\n\n"
            "{{full_name}}\n"
            "{{address}}\n\n"
            "RE: Unclaimed Surplus Funds — Your Former Property at {{property_description}}\n\n"
            "Dear {{full_name}},\n\n"
            "My name is {{assigned_to}}, and I am writing to you on behalf of "
            "{{company_name}} regarding an important financial matter.\n\n"
            "Our records indicate that the property you formerly owned at "
            "{{property_description}}, {{county}}, {{state}} (Parcel No. "
            "{{parcel_folio}}) was sold at a tax deed auction. That sale produced "
            "surplus / excess proceeds — funds above and beyond what was owed in "
            "taxes — that are currently being held by the county on your behalf.\n\n"
            "These funds legally belong to YOU.\n\n"
            "The estimated surplus amount is {{estimated_surplus}}. However, these "
            "funds will not be paid to you automatically. A claim must be filed, "
            "and if the funds remain unclaimed, they may eventually be turned over "
            "to the state.\n\n"
            "HOW WE CAN HELP\n"
            "{{company_name}} specializes in recovering surplus funds for former "
            "property owners — at NO UPFRONT COST to you. We work on a contingency "
            "basis: you pay nothing unless we successfully recover your funds.\n\n"
            "Our services include:\n"
            "  • Verifying the surplus amount on file with the county\n"
            "  • Preparing all required claim documentation\n"
            "  • Submitting the claim and following up with the county\n"
            "  • Disbursing your funds directly to you\n\n"
            "NEXT STEPS\n"
            "Simply call or email us to discuss your case. There is no obligation, "
            "and we will explain everything clearly before you sign anything.\n\n"
            "Time is important — claim deadlines exist and funds may escheat to "
            "the state if not claimed. Please contact us soon.\n\n"
            "Sincerely,\n\n"
            "{{assigned_to}}\n"
            "{{company_name}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "IMPORTANT: {{company_name}} is NOT a law firm and does not provide "
            "legal advice. This letter is for informational purposes only."
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "generated",
        "name": "Disbursements Worksheet",
        "description": "Internal worksheet tracking the disbursement of recovered surplus funds to all parties.",
        "category": "report",
        "content": (
            "DISBURSEMENTS WORKSHEET — SURPLUS FUND RECOVERY\n"
            "{{company_name}} — INTERNAL USE\n\n"
            "Case No.: {{case_number}}\n"
            "Client: {{full_name}}\n"
            "County: {{county}} | Parcel: {{parcel_folio}}\n"
            "Tax Deed No.: {{tax_deed_number}}\n"
            "Recovery Specialist: {{assigned_to}}\n"
            "Date Funds Received: {{date}}\n\n"
            "=== FUNDS RECEIVED ===\n"
            "Gross Amount Received from County:       $_______________\n"
            "Check No. / Reference:                   _______________\n"
            "Date Deposited:                          _______________\n\n"
            "=== DISBURSEMENTS ===\n"
            "1. Recovery Costs Advanced (reimbursed first):\n"
            "   Filing Fees:                          $_______________\n"
            "   Recording Fees:                       $_______________\n"
            "   Notary Fees:                          $_______________\n"
            "   Other Costs:                          $_______________\n"
            "   TOTAL COSTS:                          $_______________\n\n"
            "2. Net Funds After Costs:                $_______________\n\n"
            "3. {{company_name}} Fee ({{fee_percentage}}):\n"
            "   Fee Amount:                           $_______________\n\n"
            "4. Client Share ({{client_percentage}}):\n"
            "   Client Amount:                        $_______________\n\n"
            "5. Verification:\n"
            "   Costs + Company Fee + Client = Gross: [ ] Balanced  [ ] Discrepancy\n\n"
            "=== CLIENT PAYMENT ===\n"
            "Payment Method: [ ] Check  [ ] Wire  [ ] Cashier's Check\n"
            "Payable To: {{full_name}}\n"
            "Mailing Address: {{address}}\n"
            "Date Mailed / Wired: _______________\n"
            "Check No. / Wire Ref.: _______________\n\n"
            "=== W-9 ON FILE ===\n"
            "W-9 Received: [ ] Yes  [ ] No — required before disbursement if "
            "surplus exceeds $600.00\n\n"
            "Notes: {{notes}}\n\n"
            "Prepared by: {{assigned_to}} | {{company_name}}"
        ),
    },
    {
        "division_slug": "overages",
        "template_type": "intake",
        "name": "W-9 Request for Taxpayer Identification",
        "description": "IRS Form W-9 — sent to clients to collect their TIN/SSN before disbursing recovered funds over $600.",
        "category": "form",
        "content": (
            "REQUEST FOR TAXPAYER IDENTIFICATION NUMBER AND CERTIFICATION\n"
            "(IRS Form W-9 — Substitute)\n\n"
            "TO: {{full_name}}\n"
            "FROM: {{company_name}}\n"
            "DATE: {{date}}\n"
            "CASE NO.: {{case_number}}\n\n"
            "IMPORTANT: Federal law requires {{company_name}} to obtain your correct "
            "Taxpayer Identification Number (TIN) before disbursing any surplus fund "
            "payment of $600 or more. Please complete ALL sections below and return "
            "this form promptly.\n\n"
            "PART I — IDENTIFICATION\n"
            "Legal Name (as shown on your tax return): _______________________________\n"
            "Business / DBA Name (if different): _______________________________\n"
            "Address: _______________________________\n"
            "City, State, ZIP: _______________________________\n\n"
            "Federal Tax Classification:\n"
            "  [ ] Individual / Sole Proprietor\n"
            "  [ ] C Corporation\n"
            "  [ ] S Corporation\n"
            "  [ ] Partnership\n"
            "  [ ] Trust / Estate\n"
            "  [ ] Limited Liability Company (tax classification: _____)\n"
            "  [ ] Other: _______________________________\n\n"
            "PART II — TAXPAYER IDENTIFICATION NUMBER\n"
            "Social Security Number:          ___ ___ ___  –  ___ ___  –  ___ ___ ___ ___\n"
            "  — OR —\n"
            "Employer Identification Number:  ___ ___  –  ___ ___ ___ ___ ___ ___ ___\n\n"
            "PART III — CERTIFICATION\n"
            "Under penalties of perjury, I certify that:\n"
            "  1. The TIN shown on this form is my correct taxpayer identification "
            "number (or I am waiting for a number to be issued);\n"
            "  2. I am not subject to backup withholding;\n"
            "  3. I am a U.S. citizen or other U.S. person.\n\n"
            "Signature: _______________________________\n"
            "Printed Name: {{full_name}}\n"
            "Date: {{signature_date}}\n\n"
            "Return completed form to:\n"
            "{{company_name}} | {{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "NOTE: Failure to provide your TIN may result in mandatory backup "
            "withholding of 24% from your disbursement per IRS regulations."
        ),
    },
    # ── JUDGMENT RECOVERY — templates ─────────────────────────────────────────
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Acknowledgment of Assignment (Judgment)",
        "description": "Court-filed document transferring ownership of a civil judgment to the recovery company.",
        "category": "agreement",
        "content": (
            "ACKNOWLEDGMENT OF ASSIGNMENT OF JUDGMENT\n\n"
            "IN THE {{court_name}}\n"
            "Case / Docket No.: {{docket_number}}\n"
            "Term: {{term}}\n\n"
            "Original Plaintiff (Judgment Creditor): {{plaintiff_name}}\n"
            "Defendant (Judgment Debtor): {{defendant_name}}\n"
            "Original Judgment Amount: {{judgment_amount}}\n"
            "Judgment Date: {{date}}\n\n"
            "NOTICE OF ASSIGNMENT\n"
            "PLEASE TAKE NOTICE that {{plaintiff_name}} (\"Assignor\") has sold, "
            "assigned, and transferred all of Assignor's right, title, and interest "
            "in and to the above-captioned judgment to:\n\n"
            "{{new_plaintiff_name}}\n"
            "{{company_address}}\n\n"
            "(\"Assignee\")\n\n"
            "The Assignment was made for valuable consideration paid by Assignee to "
            "Assignor. Assignee is now the owner of the above-referenced judgment and "
            "is entitled to enforce all legal remedies available to the original "
            "judgment creditor, including but not limited to: wage garnishments, bank "
            "levies, property liens, and execution of assets.\n\n"
            "This Acknowledgment is submitted for filing with the Court pursuant to "
            "applicable court rules, to place the Court and all interested parties on "
            "notice of this Assignment.\n\n"
            "Respectfully submitted,\n\n"
            "_____________________________\n"
            "{{plaintiff_name}} (Original Judgment Creditor / Assignor)\n"
            "Date: {{signature_date}}\n\n"
            "_____________________________\n"
            "{{assigned_to}}, Authorized Representative\n"
            "{{new_plaintiff_name}} (Assignee)\n"
            "Date: {{signature_date}}\n\n"
            "Attorney ID: {{attorney_id}} | {{attorney_firm}}\n"
            "{{company_address}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Judgment Purchase Agreement",
        "description": "Private contract between judgment creditor and recovery company for purchase of a civil judgment.",
        "category": "agreement",
        "content": (
            "JUDGMENT PURCHASE AGREEMENT\n\n"
            "This Judgment Purchase Agreement (\"Agreement\") is entered into as of "
            "{{date}} by and between {{plaintiff_name}} (\"Seller\") and "
            "{{company_name}} (\"Buyer\").\n\n"
            "JUDGMENT DETAILS\n"
            "Court: {{court_name}}\n"
            "Case / Docket No.: {{docket_number}}\n"
            "Judgment Debtor: {{defendant_name}}\n"
            "Original Judgment Amount: {{judgment_amount}}\n"
            "Judgment Date: ___________\n\n"
            "PURCHASE\n"
            "Seller agrees to sell, assign, and transfer to Buyer all of Seller's "
            "right, title, and interest in the above-referenced judgment for the "
            "purchase price of $_____ (\"Purchase Price\"), receipt of which is "
            "hereby acknowledged.\n\n"
            "CONTINGENCY ARRANGEMENT\n"
            "In lieu of or in addition to the Purchase Price, upon Buyer's successful "
            "collection of any funds under the judgment, Buyer shall remit to Seller "
            "{{client_percentage}} of all amounts collected. Buyer retains "
            "{{fee_percentage}} as its recovery fee.\n\n"
            "SELLER REPRESENTATIONS\n"
            "Seller warrants that: (a) the judgment is valid, unsatisfied, and not "
            "previously assigned; (b) Seller has full authority to sell the judgment; "
            "(c) no attorney has a lien on the judgment; (d) no bankruptcy stay is "
            "in effect against the Judgment Debtor to Seller's knowledge.\n\n"
            "REVERSION\n"
            "If Buyer is unable to collect any amounts within _____ months of the "
            "date of this Agreement, ownership of the judgment shall revert to "
            "Seller upon written notice.\n\n"
            "CONFIDENTIALITY\n"
            "The terms of this Agreement are confidential and shall not be disclosed "
            "to the Judgment Debtor or any third party without mutual written consent.\n\n"
            "NOT A LAW FIRM\n"
            "{{company_name}} is NOT a law firm. Legal enforcement of judgments may "
            "require coordination with a licensed attorney.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{plaintiff_name}} (Seller)\t\t\t{{assigned_to}} (Buyer / Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}}"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Debtor Skip Trace Report",
        "description": "Internal report documenting skip tracing results for a judgment debtor.",
        "category": "report",
        "content": (
            "DEBTOR SKIP TRACE REPORT — INTERNAL\n"
            "{{company_name}}\n\n"
            "Case No.: {{case_number}}\n"
            "Date: {{date}}\n"
            "Investigator: {{assigned_to}}\n\n"
            "JUDGMENT INFORMATION\n"
            "Court: {{court_name}}\n"
            "Docket No.: {{docket_number}}\n"
            "Judgment Amount: {{judgment_amount}}\n"
            "Original Creditor (Client): {{plaintiff_name}}\n"
            "Judgment Debtor: {{defendant_name}}\n\n"
            "=== SKIP TRACE FINDINGS ===\n\n"
            "CURRENT ADDRESS:\n"
            "  Confirmed Address: _______________________________\n"
            "  Source: [ ] Credit Report  [ ] Public Record  [ ] Voter Reg.  [ ] Other: ___\n"
            "  Date Verified: _______________\n\n"
            "EMPLOYMENT:\n"
            "  Employer Name: _______________________________\n"
            "  Employer Address: _______________________________\n"
            "  Source: _______________\n"
            "  Wage Garnishment Viable: [ ] Yes  [ ] No  [ ] Unknown\n\n"
            "BANK ACCOUNTS:\n"
            "  Institution: _______________________________\n"
            "  Source: _______________\n"
            "  Bank Levy Viable: [ ] Yes  [ ] No  [ ] Unknown\n\n"
            "REAL PROPERTY OWNED:\n"
            "  Property Address / Parcel: _______________________________\n"
            "  Source: [ ] County Records  [ ] Credit Report  [ ] Other: ___\n"
            "  Lien Viable: [ ] Yes  [ ] No\n\n"
            "VEHICLES / OTHER ASSETS:\n"
            "  Description: _______________________________\n"
            "  Source: _______________\n\n"
            "RECOMMENDED ENFORCEMENT ACTION:\n"
            "  [ ] Wage Garnishment  [ ] Bank Levy  [ ] Property Lien\n"
            "  [ ] Order for Disclosure  [ ] Other: _______________________________\n\n"
            "NOTES / FLAGS:\n"
            "{{notes}}\n\n"
            "Prepared by: {{assigned_to}} | {{company_name}}\n"
            "CONFIDENTIAL — FOR INTERNAL USE ONLY"
        ),
    },
    {
        "division_slug": "judgment",
        "template_type": "generated",
        "name": "Judgment Outreach Letter (to Creditor)",
        "description": "Marketing letter sent to a judgment creditor offering to collect their uncollected judgment.",
        "category": "letter",
        "content": (
            "{{company_name}}\n"
            "{{company_address}}\n"
            "{{company_phone}} | {{company_email}}\n\n"
            "Date: {{date}}\n\n"
            "{{plaintiff_name}}\n"
            "{{address}}\n\n"
            "RE: Your Uncollected Judgment — Case No. {{docket_number}}\n\n"
            "Dear {{plaintiff_name}},\n\n"
            "We are writing regarding the civil judgment entered in your favor in "
            "{{court_name}} (Case No. {{docket_number}}) against {{defendant_name}} "
            "in the amount of {{judgment_amount}}.\n\n"
            "Our records indicate this judgment may remain uncollected. Did you know "
            "that across the United States, an estimated 75–85% of court-awarded "
            "judgments go uncollected — not because they cannot be enforced, but "
            "because most creditors lack the time, expertise, and tools to pursue "
            "collection after the court case ends?\n\n"
            "{{company_name}} specializes in judgment recovery. We can pursue "
            "collection of your judgment on your behalf through legal means — wage "
            "garnishments, bank levies, property liens, and more — AT NO UPFRONT "
            "COST TO YOU.\n\n"
            "HOW IT WORKS:\n"
            "  1. You assign your judgment to us (a simple, reversible process).\n"
            "  2. We locate the debtor and their assets using professional skip "
            "tracing resources.\n"
            "  3. We enforce collection through the court system.\n"
            "  4. When funds are recovered, you receive {{client_percentage}} of all "
            "collected amounts — we keep {{fee_percentage}} as our fee.\n"
            "  5. If we collect nothing, you owe us nothing.\n\n"
            "Please call or email us to discuss your case. There is absolutely no "
            "obligation, and we will explain everything before you make any decision.\n\n"
            "Sincerely,\n\n"
            "{{assigned_to}}\n"
            "{{company_name}}\n"
            "{{company_phone}} | {{company_email}}"
        ),
    },
    # ── NOTARY — Mobile Notary Agreement (from source document) ───────────────
    {
        "division_slug": "notary",
        "template_type": "generated",
        "name": "Mobile Notary Fee Agreement (Detailed)",
        "description": "Detailed mobile notary engagement letter with travel fee, cancellation policy, and W-9 request.",
        "category": "agreement",
        "content": (
            "MOBILE NOTARY FEE AGREEMENT\n"
            "{{company_name}}\n\n"
            "Date: {{date}}\n"
            "Client: {{full_name}}\n"
            "Case / Appointment No.: {{case_number}}\n\n"
            "APPOINTMENT DETAILS\n"
            "Date of Service: {{date}}\n"
            "Location of Service: {{address}}\n"
            "Document(s) to be Notarized: {{document_type}}\n"
            "Notary Public: {{notary_name}}\n"
            "Commission No.: {{notary_commission}}\n\n"
            "FEE SCHEDULE\n"
            "  Notarization Fee (per signature):   $_______________\n"
            "  Travel / Mobile Fee:                $_______________\n"
            "  Printing / Document Prep Fee:       $_______________\n"
            "  After-Hours / Weekend Surcharge:    $_______________\n"
            "  TOTAL FEE:                          {{notary_fee}}\n\n"
            "PAYMENT\n"
            "Payment is due at the time of service. Accepted forms of payment: "
            "[ ] Cash  [ ] Zelle  [ ] Venmo  [ ] Credit/Debit Card  [ ] Check\n\n"
            "IDENTIFICATION REQUIREMENT\n"
            "Client must present valid, unexpired government-issued photo "
            "identification at the time of signing. {{notary_name}} cannot "
            "proceed with notarization without proper identification.\n\n"
            "CANCELLATION POLICY\n"
            "Cancellations made with less than two (2) hours' notice of the "
            "scheduled appointment may be charged a cancellation / trip fee of "
            "$_______________. Cancellations with adequate notice will not be charged.\n\n"
            "REFUSAL OF SERVICE\n"
            "{{notary_name}} reserves the right to refuse service if: (a) the "
            "signer cannot be properly identified; (b) the signer appears to be "
            "signing under duress; or (c) the document appears fraudulent or "
            "incomplete.\n\n"
            "LIMITATION OF SERVICES\n"
            "{{company_name}} provides notarization services only. We do not "
            "provide legal advice, draft legal documents, or guarantee that "
            "notarized documents will be accepted by any specific agency.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Client)\t\t\t{{notary_name}} (Notary Public)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}} | {{company_phone}} | {{company_email}}"
        ),
    },
    # ── CONSULTING — Independent Contractor Agreement ─────────────────────────
    {
        "division_slug": "consulting",
        "template_type": "generated",
        "name": "Independent Contractor Agreement",
        "description": "Agreement engaging an independent contractor for surplus recovery or consulting services.",
        "category": "agreement",
        "content": (
            "INDEPENDENT CONTRACTOR AGREEMENT\n\n"
            "This Independent Contractor Agreement (\"Agreement\") is entered into "
            "as of {{date}} by and between {{company_name}} (\"Company\") and "
            "{{full_name}} (\"Contractor\").\n\n"
            "1. SERVICES\n"
            "Contractor agrees to provide the following services for Company:\n"
            "{{service_type}}\n"
            "Services shall commence on {{date}} and continue until terminated "
            "by either party upon _____ days' written notice.\n\n"
            "2. COMPENSATION\n"
            "Company shall pay Contractor as follows:\n"
            "  [ ] Flat Fee: $_______________  per _______________\n"
            "  [ ] Hourly Rate: $_______________  per hour\n"
            "  [ ] Commission: {{fee_percentage}} of revenues generated\n"
            "Payment shall be made within _____ days of invoice.\n\n"
            "3. INDEPENDENT CONTRACTOR STATUS\n"
            "Contractor is an independent contractor and NOT an employee of Company. "
            "Contractor is responsible for all self-employment taxes, insurance, and "
            "compliance with applicable laws. Company shall not withhold taxes on "
            "Contractor's behalf. Contractor shall provide a completed IRS Form W-9 "
            "prior to first payment.\n\n"
            "4. CONFIDENTIALITY\n"
            "Contractor agrees to keep confidential all client information, business "
            "methods, proprietary data, and trade secrets learned during the term "
            "of this Agreement, both during and after its termination.\n\n"
            "5. NON-SOLICITATION\n"
            "During the term of this Agreement and for twelve (12) months thereafter, "
            "Contractor agrees not to solicit Company's clients directly for "
            "competing services.\n\n"
            "6. WORK PRODUCT\n"
            "All work product, reports, and deliverables produced by Contractor in "
            "connection with Company's clients shall be the property of Company.\n\n"
            "7. TERMINATION\n"
            "Either party may terminate this Agreement with _____ days' written "
            "notice. Company may terminate immediately for cause.\n\n"
            "8. GOVERNING LAW\n"
            "This Agreement is governed by the laws of South Carolina.\n\n"
            "_____________________________\t\t_____________________________\n"
            "{{full_name}} (Contractor)\t\t\t{{assigned_to}} (Company)\n"
            "Date: {{signature_date}}\t\t\tDate: {{signature_date}}\n\n"
            "{{company_name}} | {{company_address}}"
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
