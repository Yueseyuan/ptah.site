from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class AegisClient(Base):
    __tablename__ = "aegis_clients"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String)
    last_name = Column(String)
    email = Column(String, index=True)
    phone = Column(String)
    address = Column(String)
    city = Column(String)
    state = Column(String, default="SC")
    zip_code = Column(String)
    dob = Column(String)
    ssn_last4 = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    # Portal link — the User account this client uses to log into the portal
    portal_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    cases = relationship("AegisCase", back_populates="client")
    court_records = relationship("CourtRecord", back_populates="client")
    portal_documents = relationship("ClientDocument", back_populates="client")


class AegisCase(Base):
    __tablename__ = "aegis_cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    case_number = Column(String, unique=True, index=True)
    status = Column(String, default="intake")  # intake, active, on_hold, closed
    portal_status = Column(String, default="pending")  # pending, docs_needed, under_review, active, completed
    goal = Column(Text)
    notes = Column(Text)
    assigned_to = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    client = relationship("AegisClient", back_populates="cases")
    reports = relationship("CreditReport", back_populates="case")
    tradelines = relationship("Tradeline", back_populates="case")
    comparisons = relationship("TradelineComparison", back_populates="case")
    findings = relationship("Finding", back_populates="case")
    evidence = relationship("EvidenceItem", back_populates="case")
    court_records = relationship("CourtRecord", back_populates="case")
    timeline_events = relationship("TimelineEvent", back_populates="case")
    strategy_items = relationship("StrategyItem", back_populates="case")
    generated_reports = relationship("GeneratedReport", back_populates="case")
    dispute_rounds = relationship("DisputeRound", back_populates="case")
    outcomes = relationship("Outcome", back_populates="case")
    metro2_findings = relationship("Metro2Finding", back_populates="case")
    inquiries = relationship("Inquiry", back_populates="case")
    personal_info_records = relationship("PersonalInfo", back_populates="case")


class CreditReport(Base):
    __tablename__ = "credit_reports"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    bureau = Column(String)  # experian, equifax, transunion, innovis
    file_path = Column(String)
    raw_text = Column(Text)
    parse_status = Column(String, default="pending")  # pending, parsed, failed
    report_date = Column(String)
    parse_error = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="reports")
    tradelines = relationship("Tradeline", back_populates="report")


class Tradeline(Base):
    __tablename__ = "tradelines"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    report_id = Column(Integer, ForeignKey("credit_reports.id"))
    bureau = Column(String)
    creditor_name = Column(String)
    account_number_last4 = Column(String)
    account_type = Column(String)
    open_date = Column(String)
    close_date = Column(String)
    balance = Column(Float, nullable=True)
    credit_limit = Column(Float, nullable=True)
    payment_status = Column(String)
    payment_history = Column(Text)  # JSON
    derogatory = Column(Boolean, default=False)
    dispute_status = Column(String, default="none")  # none, in_dispute, resolved
    # Metro 2 fields
    high_balance = Column(Float, nullable=True)
    past_due_amount = Column(Float, nullable=True)
    scheduled_payment_amount = Column(Float, nullable=True)
    payment_rating = Column(String)          # Metro 2: 0=too new, 1=current, 2-9=days late, B=no hist, etc.
    compliance_condition_code = Column(String)  # XF, XH, XJ, XR, XO, X1-X9, XA, XB
    consumer_information_indicator = Column(String)  # A-J bankruptcy codes
    dofd = Column(String)                    # Date of First Delinquency YYYY-MM-DD
    date_reported = Column(String)
    remarks = Column(Text)
    raw_source_text = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="tradelines")
    report = relationship("CreditReport", back_populates="tradelines")
    findings = relationship("Finding", back_populates="tradeline")
    dispute_items = relationship("DisputeItem", back_populates="tradeline")
    outcomes = relationship("Outcome", back_populates="tradeline")
    metro2_findings = relationship("Metro2Finding", back_populates="tradeline")


class Metro2Finding(Base):
    __tablename__ = "metro2_findings"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    tradeline_id = Column(Integer, ForeignKey("tradelines.id"), nullable=True)
    rule_code = Column(String)      # e.g. "DOFD_7YR", "MISSING_DOFD", "BALANCE_EXCEEDS_HIGH"
    rule_name = Column(String)
    severity = Column(String, default="medium")  # high, medium, low, info
    description = Column(Text)
    fcra_section = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="metro2_findings")
    tradeline = relationship("Tradeline", back_populates="metro2_findings")


class TradelineComparison(Base):
    __tablename__ = "tradeline_comparisons"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    creditor_name = Column(String)
    account_number_last4 = Column(String)
    discrepancy_type = Column(String)  # balance, status, date, missing
    bureaus_affected = Column(Text)  # JSON list
    details = Column(Text)
    severity = Column(String, default="medium")  # high, medium, low
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="comparisons")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    tradeline_id = Column(Integer, ForeignKey("tradelines.id"), nullable=True)
    finding_type = Column(String)  # fcra_violation, discrepancy, derogatory, positive
    severity = Column(String, default="medium")  # high, medium, low, info
    title = Column(String)
    description = Column(Text)
    fcra_section = Column(String)
    evidence_ids = Column(Text)  # JSON list of EvidenceItem IDs
    requires_human_review = Column(Boolean, default=True)  # always True — compliance
    status = Column(String, default="open")  # open, reviewed, actioned, dismissed
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="findings")
    tradeline = relationship("Tradeline", back_populates="findings")


class EvidenceItem(Base):
    __tablename__ = "evidence_items"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    evidence_type = Column(String)  # bureau_response, payment_record, correspondence, screenshot
    title = Column(String)
    description = Column(Text)
    file_path = Column(String)
    source = Column(String)
    collected_at = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="evidence")


class CourtRecord(Base):
    __tablename__ = "court_records"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    case_id = Column(Integer, ForeignKey("aegis_cases.id"), nullable=True)
    record_type = Column(String)  # criminal, civil, bankruptcy, judgment, lien
    court_name = Column(String)
    jurisdiction = Column(String)
    docket_number = Column(String)
    offense_date = Column(String)
    disposition = Column(String)
    disposition_date = Column(String)
    expungement_eligible = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    client = relationship("AegisClient", back_populates="court_records")
    case = relationship("AegisCase", back_populates="court_records")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    event_type = Column(String)  # account_opened, derogatory_reported, dispute_sent, response_received, payment
    event_date = Column(String)
    title = Column(String)
    description = Column(Text)
    source = Column(String)
    related_finding_id = Column(Integer, ForeignKey("findings.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="timeline_events")


class StrategyItem(Base):
    __tablename__ = "strategy_items"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    priority = Column(Integer, default=2)  # 1=high, 2=medium, 3=low
    strategy_type = Column(String)  # dispute, goodwill, validation, pay_for_delete, consolidation
    title = Column(String)
    description = Column(Text)
    action_items = Column(Text)  # JSON list
    estimated_timeline = Column(String)
    status = Column(String, default="pending")  # pending, in_progress, completed, dismissed
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="strategy_items")


class GeneratedReport(Base):
    __tablename__ = "generated_reports"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    report_type = Column(String)  # summary, dispute_letter, strategy, full
    file_path = Column(String)
    notes = Column(Text)
    generated_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="generated_reports")


class DisputeRound(Base):
    __tablename__ = "dispute_rounds"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    round_number = Column(Integer, default=1)
    recipient_type = Column(String, default="bureau")  # bureau, creditor, collection_agency, debt_buyer
    bureau = Column(String)
    recipient_name = Column(String)
    recipient_address = Column(Text)
    sent_date = Column(String)
    response_due_date = Column(String)
    response_received_date = Column(String)
    certified_mail_tracking = Column(String)
    status = Column(String, default="preparing")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="dispute_rounds")
    items = relationship("DisputeItem", back_populates="round")


class DisputeItem(Base):
    __tablename__ = "dispute_items"
    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("dispute_rounds.id"))
    tradeline_id = Column(Integer, ForeignKey("tradelines.id"), nullable=True)
    creditor_name = Column(String)
    account_number_last4 = Column(String)
    dispute_reason = Column(String)
    fcra_basis = Column(String)
    resolution = Column(String)
    status = Column(String, default="pending")  # pending, deleted, updated, verified, no_response
    created_at = Column(DateTime, server_default=func.now())
    round = relationship("DisputeRound", back_populates="items")
    tradeline = relationship("Tradeline", back_populates="dispute_items")


class Outcome(Base):
    __tablename__ = "outcomes"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    tradeline_id = Column(Integer, ForeignKey("tradelines.id"), nullable=True)
    outcome_type = Column(String)  # deleted, updated, score_increase, letter_sent, goodwill_approved
    description = Column(Text)
    bureau = Column(String)
    achieved_date = Column(String)
    verified = Column(Boolean, default=False)
    score_before = Column(Integer, nullable=True)
    score_after = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="outcomes")
    tradeline = relationship("Tradeline", back_populates="outcomes")


class LearningEntry(Base):
    __tablename__ = "learning_entries"
    id = Column(Integer, primary_key=True, index=True)
    bureau = Column(String)
    creditor_name = Column(String)
    tactic_used = Column(String)
    fcra_basis = Column(String)
    outcome = Column(String)  # success, partial, failure
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    email = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    hashed_password = Column(String)
    role = Column(String, default="investigator")   # admin, investigator, reviewer, readonly
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    # Stripe billing
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)  # active, past_due, canceled, trialing
    subscription_period_end = Column(DateTime, nullable=True)
    organization = relationship("Organization", back_populates="users")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    action = Column(String)            # CREATE, UPDATE, DELETE, LOGIN, etc.
    resource_type = Column(String)     # client, case, tradeline, finding, etc.
    resource_id = Column(Integer, nullable=True)
    detail = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Inquiry(Base):
    __tablename__ = "inquiries"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    report_id = Column(Integer, ForeignKey("credit_reports.id"), nullable=True)
    bureau = Column(String)
    inquiry_type = Column(String, default="hard")  # hard, soft
    subscriber_name = Column(String)
    inquiry_date = Column(String)
    purpose = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="inquiries")


class PersonalInfo(Base):
    __tablename__ = "personal_info"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    report_id = Column(Integer, ForeignKey("credit_reports.id"), nullable=True)
    bureau = Column(String)
    current_name = Column(String)
    aliases = Column(Text)           # JSON list of strings
    current_address = Column(String)
    previous_addresses = Column(Text)   # JSON list of strings
    current_employer = Column(String)
    previous_employers = Column(Text)   # JSON list of strings
    phone_numbers = Column(Text)      # JSON list of strings
    dob = Column(String)
    ssn_last4 = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("AegisCase", back_populates="personal_info_records")


class FederalLaw(Base):
    __tablename__ = "federal_laws"
    id = Column(Integer, primary_key=True, index=True)
    short_name = Column(String)      # "FCRA", "FDCPA"
    title = Column(String)           # "Fair Credit Reporting Act"
    citation = Column(String)        # "15 U.S.C. § 1681 et seq."
    section = Column(String)         # "§605(a)"
    summary = Column(Text)
    effective_date = Column(String)
    category = Column(String)        # "credit_reporting", "debt_collection"
    source_url = Column(String)
    effective_as_of = Column(String)
    superseded_by_id = Column(Integer, ForeignKey("federal_laws.id"), nullable=True)
    version_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class AgencyGuidance(Base):
    __tablename__ = "agency_guidance"
    id = Column(Integer, primary_key=True, index=True)
    agency = Column(String)           # "CFPB", "FTC"
    document_name = Column(String)
    publication_date = Column(String)
    topic = Column(String)
    summary = Column(Text)
    source_url = Column(String)
    effective_as_of = Column(String)
    superseded = Column(Boolean, default=False)
    version_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class StateLaw(Base):
    __tablename__ = "state_laws"
    id = Column(Integer, primary_key=True, index=True)
    state = Column(String)            # "SC", "NY"
    statute = Column(String)
    citation = Column(String)
    topic = Column(String)
    effective_date = Column(String)
    summary = Column(Text)
    source_url = Column(String)
    effective_as_of = Column(String)
    superseded = Column(Boolean, default=False)
    version_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class ClientDocument(Base):
    """Documents uploaded by clients through the portal (credit reports, ID, supporting docs)."""
    __tablename__ = "client_documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("aegis_cases.id"))
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    # credit_report_experian | credit_report_equifax | credit_report_transunion
    # drivers_license | proof_of_address | supporting_doc | other
    doc_type = Column(String)
    bureau = Column(String, nullable=True)      # populated for credit_report_* types
    original_filename = Column(String)
    file_path = Column(String)
    notes = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now())
    reviewed = Column(Boolean, default=False)   # staff marks reviewed
    client = relationship("AegisClient", back_populates="portal_documents")


class CaseLaw(Base):
    __tablename__ = "case_law"
    id = Column(Integer, primary_key=True, index=True)
    case_name = Column(String)
    citation = Column(String)
    court = Column(String)
    jurisdiction = Column(String)
    year = Column(Integer)
    topic = Column(String)
    holding_summary = Column(Text)
    legal_principle = Column(Text)
    relevance_tags = Column(Text)    # JSON list of strings
    source_url = Column(String)
    created_at = Column(DateTime, server_default=func.now())


class LegalUpdate(Base):
    __tablename__ = "legal_updates"
    id = Column(Integer, primary_key=True, index=True)
    update_type = Column(String)       # "federal", "guidance", "state", "case_law"
    title = Column(String)
    source_url = Column(String)
    summary = Column(Text)
    proposed_changes = Column(Text)    # JSON describing what would be added/changed
    status = Column(String, default="pending")  # pending, approved, rejected
    submitted_by = Column(String)
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


# ═══════════════════════════════════════════════════════════
# DOCUMENT AUTOMATION SYSTEM — Cruel & Associates Services
# ═══════════════════════════════════════════════════════════

class ServiceCase(Base):
    """A case for any of the 6 service divisions (not credit-specific)."""
    __tablename__ = "service_cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    division_slug = Column(String, index=True)  # notary|credit|criminal|document|judgment|consulting
    case_number = Column(String, unique=True, index=True)
    status = Column(String, default="intake")  # intake|active|on_hold|closed
    title = Column(String)
    intake_data = Column(Text)   # JSON blob of intake form answers
    notes = Column(Text)
    assigned_to = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    client = relationship("AegisClient", backref="service_cases")
    service_documents = relationship("ServiceDocument", back_populates="service_case")
    appointments = relationship("Appointment", back_populates="service_case")
    invoices = relationship("ServiceInvoice", back_populates="service_case")
    referrals = relationship("AttorneyReferral", back_populates="service_case")
    notary_logs = relationship("NotaryLog", back_populates="service_case")


class DocumentTemplate(Base):
    """Reusable templates with {{variable}} placeholders for document generation."""
    __tablename__ = "document_templates"
    id = Column(Integer, primary_key=True, index=True)
    division_slug = Column(String, index=True)
    template_type = Column(String, default="generated")  # intake|generated
    name = Column(String)
    description = Column(Text)
    content = Column(Text)       # template body with {{first_name}}-style vars
    variables = Column(Text)     # JSON list of required variable names
    category = Column(String)    # agreement|letter|report|log|form|packet
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    documents = relationship("ServiceDocument", back_populates="template")


class ServiceDocument(Base):
    """AI-generated document instance, ready for e-signature or download."""
    __tablename__ = "service_documents"
    id = Column(Integer, primary_key=True, index=True)
    service_case_id = Column(Integer, ForeignKey("service_cases.id"))
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    template_id = Column(Integer, ForeignKey("document_templates.id"), nullable=True)
    division_slug = Column(String)
    title = Column(String)
    document_type = Column(String)   # agreement|letter|report|log|form|packet
    content = Column(Text)           # final rendered content
    file_path = Column(String)       # path to PDF on disk
    status = Column(String, default="draft")  # draft|pending_sign|signed|archived
    esign_request_id = Column(String, nullable=True)
    esign_provider = Column(String, nullable=True)  # docusign|dropboxsign
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    service_case = relationship("ServiceCase", back_populates="service_documents")
    template = relationship("DocumentTemplate", back_populates="documents")
    client = relationship("AegisClient", backref="service_documents")


class Appointment(Base):
    """Scheduled appointments across all service divisions."""
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    service_case_id = Column(Integer, ForeignKey("service_cases.id"), nullable=True)
    division_slug = Column(String)
    appointment_type = Column(String)  # signing|consultation|document_review|intake
    scheduled_at = Column(DateTime)
    duration_minutes = Column(Integer, default=60)
    location = Column(String)
    travel_miles = Column(Float, nullable=True)
    status = Column(String, default="scheduled")  # scheduled|confirmed|completed|cancelled
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    service_case = relationship("ServiceCase", back_populates="appointments")
    client = relationship("AegisClient", backref="appointments")


class ServiceInvoice(Base):
    """Invoice for any service rendered."""
    __tablename__ = "service_invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    service_case_id = Column(Integer, ForeignKey("service_cases.id"), nullable=True)
    invoice_number = Column(String, unique=True, index=True)
    division_slug = Column(String)
    line_items = Column(Text)    # JSON: [{description, quantity, unit_price, total}]
    subtotal = Column(Float, default=0.0)
    tax_rate = Column(Float, default=0.0)
    tax_amount = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    status = Column(String, default="draft")  # draft|sent|paid|void
    due_date = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    service_case = relationship("ServiceCase", back_populates="invoices")
    client = relationship("AegisClient", backref="service_invoices")


class AttorneyReferral(Base):
    """Attorney referral record — required for criminal and legal matters."""
    __tablename__ = "attorney_referrals"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    service_case_id = Column(Integer, ForeignKey("service_cases.id"), nullable=True)
    attorney_name = Column(String)
    attorney_firm = Column(String)
    attorney_email = Column(String)
    attorney_phone = Column(String)
    practice_area = Column(String)
    reason = Column(Text)
    status = Column(String, default="pending")  # pending|accepted|declined|completed
    referral_letter_path = Column(String, nullable=True)
    notes = Column(Text)
    referred_at = Column(DateTime, server_default=func.now())
    service_case = relationship("ServiceCase", back_populates="referrals")
    client = relationship("AegisClient", backref="attorney_referrals")


class NotaryLog(Base):
    """Official notary journal entry for every notarized document."""
    __tablename__ = "notary_logs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("aegis_clients.id"))
    service_case_id = Column(Integer, ForeignKey("service_cases.id"), nullable=True)
    journal_number = Column(String, unique=True, index=True)
    document_type = Column(String)
    signer_name = Column(String)
    signer_id_type = Column(String)      # passport|drivers_license|state_id
    signer_id_number = Column(String)
    signer_id_expiry = Column(String)
    num_signers = Column(Integer, default=1)
    num_witnesses = Column(Integer, default=0)
    notarized_at = Column(DateTime)
    location = Column(String)
    travel_miles = Column(Float, nullable=True)
    fee_charged = Column(Float, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    service_case = relationship("ServiceCase", back_populates="notary_logs")
    client = relationship("AegisClient", backref="notary_logs")
