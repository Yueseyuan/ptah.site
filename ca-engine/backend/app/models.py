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
