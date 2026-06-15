from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    role = Column(String, default="staff")  # admin, staff, client
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Client(Base):
    __tablename__ = "clients"
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
    cases = relationship("Case", back_populates="client")
    invoices = relationship("Invoice", back_populates="client")

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    division = Column(String)  # notary, credit, reentry, document_prep, asset_recovery, business
    title = Column(String)
    description = Column(Text)
    status = Column(String, default="active")
    intake_data = Column(Text)  # JSON blob of all intake fields
    ai_analysis = Column(Text)  # AI-generated analysis
    notes = Column(Text)
    assigned_to = Column(String)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    client = relationship("Client", back_populates="cases")
    documents = relationship("Document", back_populates="case")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    document_type = Column(String)
    label = Column(String)
    file_path = Column(String)
    pdf_path = Column(String)
    status = Column(String, default="draft")  # draft, pending_signature, signed, archived
    esign_envelope_id = Column(String)
    esign_provider = Column(String)
    signed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    case = relationship("Case", back_populates="documents")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    case_id = Column(Integer, ForeignKey("cases.id"))
    amount = Column(Float)
    paid = Column(Float, default=0.0)
    status = Column(String, default="pending")
    notes = Column(Text)
    due_date = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    client = relationship("Client", back_populates="invoices")

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    case_id = Column(Integer, ForeignKey("cases.id"))
    division = Column(String)
    appointment_type = Column(String)  # phone, in_person, virtual
    scheduled_at = Column(DateTime)
    duration_minutes = Column(Integer, default=30)
    status = Column(String, default="scheduled")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

class NotaryLog(Base):
    __tablename__ = "notary_logs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    document_type = Column(String)
    num_acts = Column(Integer, default=1)
    fee_per_act = Column(Float, default=5.0)
    travel_fee = Column(Float, default=0.0)
    service_fee = Column(Float, default=0.0)
    location = Column(String)
    notarized_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)
    resource_type = Column(String)
    resource_id = Column(Integer)
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ── Division 1 — Notary Jobs ──────────────────────────────────────────────────

class NotaryJob(Base):
    __tablename__ = "notary_jobs"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    job_number = Column(String, unique=True, index=True)
    job_type = Column(String)
    service_mode = Column(String, default="in_person")
    status = Column(String, default="scheduled")
    appointment_at = Column(DateTime)
    document_type = Column(String)
    num_signers = Column(Integer, default=1)
    travel_miles = Column(Float, default=0.0)
    signing_company = Column(String)
    base_fee = Column(Float, default=75.0)
    travel_fee = Column(Float, default=0.0)
    signer_fee = Column(Float, default=0.0)
    total_fee = Column(Float, default=0.0)
    platform_source = Column(String, default="manual")
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


# ── Division 2 — Credit ───────────────────────────────────────────────────────

class CreditCase(Base):
    __tablename__ = "credit_cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    case_number = Column(String, unique=True, index=True)
    status = Column(String, default="intake")
    starting_score_eq = Column(Integer)
    starting_score_ex = Column(Integer)
    starting_score_tu = Column(Integer)
    current_score_eq = Column(Integer)
    current_score_ex = Column(Integer)
    current_score_tu = Column(Integer)
    total_negative_items = Column(Integer, default=0)
    items_removed = Column(Integer, default=0)
    items_in_dispute = Column(Integer, default=0)
    first_work_completed = Column(Boolean, default=False)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    dispute_items = relationship("DisputeItem", back_populates="credit_case")

class DisputeItem(Base):
    __tablename__ = "dispute_items"
    id = Column(Integer, primary_key=True, index=True)
    credit_case_id = Column(Integer, ForeignKey("credit_cases.id"))
    bureau = Column(String)
    creditor_name = Column(String)
    account_last4 = Column(String)
    item_type = Column(String)
    dispute_reason = Column(String)
    fcra_basis = Column(String)
    status = Column(String, default="pending")
    letter_sent_at = Column(DateTime, nullable=True)
    response_due_at = Column(DateTime, nullable=True)
    bureau_response_at = Column(DateTime, nullable=True)
    resolution = Column(String)
    priority = Column(Integer, default=2)
    created_at = Column(DateTime, server_default=func.now())
    credit_case = relationship("CreditCase", back_populates="dispute_items")


# ── Division 3 — Criminal Relief ─────────────────────────────────────────────

class ReliefCase(Base):
    __tablename__ = "relief_cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    case_number = Column(String, unique=True, index=True)
    status = Column(String, default="intake")
    service_tier = Column(String, default="standard")
    needs_attorney = Column(Boolean, default=False)
    referral_reason = Column(Text)
    referral_sent = Column(Boolean, default=False)
    target_employer = Column(String)
    target_landlord = Column(String)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    criminal_records = relationship("CriminalRecord", back_populates="relief_case")

class CriminalRecord(Base):
    __tablename__ = "criminal_records"
    id = Column(Integer, primary_key=True, index=True)
    relief_case_id = Column(Integer, ForeignKey("relief_cases.id"))
    offense_type = Column(String)
    offense_date = Column(String)
    jurisdiction = Column(String)
    court_name = Column(String)
    disposition = Column(String)
    sentence = Column(Text)
    release_date = Column(String)
    probation_end = Column(String)
    rehabilitation_notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    relief_case = relationship("ReliefCase", back_populates="criminal_records")


# ── Division 4 — Doc Prep ─────────────────────────────────────────────────────

class DocPrepOrder(Base):
    __tablename__ = "docprep_orders"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    order_number = Column(String, unique=True, index=True)
    status = Column(String, default="pending")
    doc_category = Column(String, default="general")
    doc_types = Column(Text)       # JSON
    intake_data = Column(Text)     # JSON
    total_fee = Column(Float, default=50.0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    hkp_instruments = relationship("HKPInstrument", back_populates="order")

class HKPInstrument(Base):
    __tablename__ = "hkp_instruments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("docprep_orders.id"))
    instrument_type = Column(String)
    member_name = Column(String)
    member_address = Column(Text)
    instrument_amount = Column(Float, nullable=True)
    interest_rate = Column(Float, nullable=True)
    term_months = Column(Integer, nullable=True)
    maturity_date = Column(String)
    collateral_description = Column(Text)
    profit_sharing_terms = Column(Text)
    inheritance_transfer = Column(Boolean, default=False)
    beneficiary_name = Column(String)
    signatory_title = Column(String, default="Netjer-Tepi")
    created_at = Column(DateTime, server_default=func.now())
    order = relationship("DocPrepOrder", back_populates="hkp_instruments")


# ── Division 5 — Recovery ─────────────────────────────────────────────────────

class RecoveryCase(Base):
    __tablename__ = "recovery_cases"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    case_number = Column(String, unique=True, index=True)
    case_type = Column(String)
    status = Column(String, default="intake")
    subject_name = Column(String)
    subject_ssn_last4 = Column(String)
    subject_dob = Column(String)
    claimant_relationship = Column(String)
    states_searched = Column(Text)   # JSON array
    total_found = Column(Float, default=0.0)
    total_recovered = Column(Float, default=0.0)
    contingency_pct = Column(Float, default=30.0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    assets = relationship("RecoveryAsset", back_populates="recovery_case")

class RecoveryAsset(Base):
    __tablename__ = "recovery_assets"
    id = Column(Integer, primary_key=True, index=True)
    recovery_case_id = Column(Integer, ForeignKey("recovery_cases.id"))
    source_state = Column(String)
    source_agency = Column(String)
    asset_type = Column(String)
    holder_name = Column(String)
    reported_amount = Column(Float)
    recovered_amount = Column(Float, nullable=True)
    property_id = Column(String)
    claim_reference = Column(String)
    status = Column(String, default="located")
    created_at = Column(DateTime, server_default=func.now())
    recovery_case = relationship("RecoveryCase", back_populates="assets")


# ── Division 6 — Consulting ───────────────────────────────────────────────────

class ConsultingEngagement(Base):
    __tablename__ = "consulting_engagements"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    engagement_number = Column(String, unique=True, index=True)
    status = Column(String, default="scheduled")
    engagement_type = Column(String, default="hourly")
    business_stage = Column(String)
    business_type = Column(String)
    goals = Column(Text)                   # JSON
    session_datetime = Column(DateTime, nullable=True)
    session_notes = Column(Text)
    action_items = Column(Text)            # JSON
    recommended_services = Column(Text)    # JSON
    total_fee = Column(Float, default=150.0)
    notes = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    consulting_documents = relationship("ConsultingDocument", back_populates="engagement")

class ConsultingDocument(Base):
    __tablename__ = "consulting_documents"
    id = Column(Integer, primary_key=True, index=True)
    engagement_id = Column(Integer, ForeignKey("consulting_engagements.id"))
    doc_type = Column(String)
    file_path = Column(String)
    ai_generated = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    engagement = relationship("ConsultingEngagement", back_populates="consulting_documents")
