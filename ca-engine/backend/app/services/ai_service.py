"""
AI service: Claude (primary) + OpenAI (fallback) for document enhancement,
credit analysis, reentry narratives, and intake processing.
"""
import json
from typing import Any, Dict, List, Optional

from app.config import settings

# ── Lazy client creation ──────────────────────────────────────────────────────

def _anthropic_client():
    if not settings.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not configured")
    import anthropic
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _openai_client():
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# ── Core completions ──────────────────────────────────────────────────────────

def _claude(system: str, user: str, max_tokens: int = 2048) -> str:
    client = _anthropic_client()
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text.strip()


def _openai(system: str, user: str, max_tokens: int = 2048) -> str:
    client = _openai_client()
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content.strip()


def complete(system: str, user: str, max_tokens: int = 2048) -> str:
    """Try Claude first, fall back to OpenAI."""
    try:
        return _claude(system, user, max_tokens)
    except Exception:
        return _openai(system, user, max_tokens)


# ── SYSTEM PROMPTS ────────────────────────────────────────────────────────────

_BASE_SYSTEM = (
    "You are an expert administrative services assistant for Cruel & Associates, a South Carolina "
    "administrative services firm. You assist with document preparation, administrative guidance, "
    "and client communications. You are NOT an attorney and must never provide legal advice. "
    "All outputs are for administrative document preparation purposes only. "
    "Always be professional, precise, and compliant with South Carolina regulations."
)

_CREDIT_SYSTEM = _BASE_SYSTEM + (
    " You specialize in credit report analysis and dispute letter drafting. "
    "You understand FCRA (Fair Credit Reporting Act) procedures and bureau response timelines. "
    "You draft clear, factual dispute letters based on consumer credit data."
)

_REENTRY_SYSTEM = _BASE_SYSTEM + (
    " You specialize in reentry administrative support for individuals with criminal records. "
    "You prepare employment explanation letters, character references, pardon support packets, "
    "and other administrative documents. You never provide legal advice about expungement or "
    "court proceedings — you refer clients to licensed attorneys for legal matters. "
    "Your tone is professional, compassionate, and focused on rehabilitation."
)

_BUSINESS_SYSTEM = _BASE_SYSTEM + (
    " You specialize in business formation guidance and administrative document preparation "
    "for small businesses and LLCs in South Carolina. You help with checklists, business plans, "
    "and administrative correspondence."
)

_DOCUMENT_SYSTEM = _BASE_SYSTEM + (
    " You enhance and polish administrative documents. Improve clarity, professionalism, "
    "and completeness while preserving all factual content. Never add legal claims or advice."
)


# ── PUBLIC API ────────────────────────────────────────────────────────────────

def analyze_intake(division: str, intake_data: Dict[str, Any]) -> str:
    """Generate AI analysis of a new case intake."""
    division_display = division.replace("_", " ").title()
    prompt = (
        f"Division: {division_display}\n\n"
        f"Intake Data:\n{json.dumps(intake_data, indent=2)}\n\n"
        "Please provide:\n"
        "1. A brief case summary (2-3 sentences)\n"
        "2. Key action items for the staff (numbered list)\n"
        "3. Recommended documents to prepare\n"
        "4. Any flags or concerns to address\n\n"
        "Keep it concise and actionable."
    )
    return complete(_BASE_SYSTEM, prompt, max_tokens=1024)


def analyze_credit_report(credit_data: Dict[str, Any]) -> str:
    """Analyze credit report data and identify dispute opportunities."""
    prompt = (
        f"Credit Report Data:\n{json.dumps(credit_data, indent=2)}\n\n"
        "Analyze this credit report and provide:\n"
        "1. Overall credit health assessment\n"
        "2. Negative items eligible for dispute (FCRA basis for each)\n"
        "3. Recommended dispute strategy and priority order\n"
        "4. Expected timeline for improvements\n"
        "5. Credit-building recommendations\n\n"
        "Be specific about FCRA sections where applicable. Do not provide legal advice."
    )
    return complete(_CREDIT_SYSTEM, prompt, max_tokens=1500)


def generate_dispute_narrative(
    item_type: str,
    creditor: str,
    account_number: str,
    reason: str,
    client_statement: Optional[str] = None,
) -> str:
    """Generate a professional dispute narrative for a credit item."""
    prompt = (
        f"Item Type: {item_type}\n"
        f"Creditor/Furnisher: {creditor}\n"
        f"Account: {account_number}\n"
        f"Dispute Reason: {reason}\n"
        f"Client Statement: {client_statement or 'N/A'}\n\n"
        "Write a professional, FCRA-compliant dispute narrative (2-4 paragraphs) for inclusion "
        "in a credit bureau dispute letter. Be factual, cite the consumer's rights under FCRA "
        "§ 611, and request specific investigation and correction/deletion. "
        "Do not make legal threats or promise outcomes."
    )
    return complete(_CREDIT_SYSTEM, prompt, max_tokens=600)


def generate_reentry_narrative(
    client_name: str,
    offense_description: str,
    years_since: int,
    rehabilitation_highlights: List[str],
    purpose: str = "employment",
) -> str:
    """Generate a reentry narrative for employment or housing applications."""
    highlights_text = "\n".join(f"- {h}" for h in rehabilitation_highlights)
    prompt = (
        f"Client Name: {client_name}\n"
        f"Offense Description: {offense_description}\n"
        f"Years Since Offense/Release: {years_since}\n"
        f"Rehabilitation Highlights:\n{highlights_text}\n"
        f"Document Purpose: {purpose}\n\n"
        "Write a professional, honest, and compassionate personal narrative (3-5 paragraphs) "
        "for this individual's reentry support document. Focus on accountability, growth, "
        "and future contributions. This is for administrative document preparation only — "
        "not legal representation. The tone should be genuine and professional."
    )
    return complete(_REENTRY_SYSTEM, prompt, max_tokens=800)


def generate_employment_explanation(
    client_name: str,
    employer_name: str,
    offense_description: str,
    years_since: int,
    skills: List[str],
    work_history: Optional[str] = None,
) -> str:
    """Generate an employment explanation letter body."""
    skills_text = ", ".join(skills) if skills else "various administrative and vocational skills"
    prompt = (
        f"Client: {client_name}\n"
        f"Prospective Employer: {employer_name}\n"
        f"Offense: {offense_description}\n"
        f"Years Since: {years_since}\n"
        f"Relevant Skills: {skills_text}\n"
        f"Work History Summary: {work_history or 'Not provided'}\n\n"
        "Write a professional employment explanation letter body (3-4 paragraphs). "
        "The letter should acknowledge the past, demonstrate accountability and change, "
        "highlight relevant skills, and make a compelling case for employment consideration. "
        "Avoid minimizing the offense. Focus on present qualifications and future potential."
    )
    return complete(_REENTRY_SYSTEM, prompt, max_tokens=700)


def generate_business_plan_section(
    business_name: str,
    business_type: str,
    services: List[str],
    target_market: str,
    section: str = "executive_summary",
) -> str:
    """Generate a specific section of a business plan."""
    services_text = ", ".join(services) if services else "various services"
    section_display = section.replace("_", " ").title()
    prompt = (
        f"Business Name: {business_name}\n"
        f"Business Type: {business_type}\n"
        f"Services: {services_text}\n"
        f"Target Market: {target_market}\n"
        f"Section to Write: {section_display}\n\n"
        f"Write the {section_display} section for this business plan. "
        "Be professional, specific, and realistic. Include relevant market considerations "
        "for South Carolina if applicable."
    )
    return complete(_BUSINESS_SYSTEM, prompt, max_tokens=1000)


def enhance_document(document_text: str, document_type: str, tone: str = "professional") -> str:
    """Polish and enhance an existing document draft."""
    prompt = (
        f"Document Type: {document_type.replace('_', ' ').title()}\n"
        f"Desired Tone: {tone}\n\n"
        f"Document to Enhance:\n---\n{document_text}\n---\n\n"
        "Improve this document for clarity, professionalism, and completeness. "
        "Preserve all factual content and the original intent. "
        "Return only the enhanced document text, no commentary."
    )
    return complete(_DOCUMENT_SYSTEM, prompt, max_tokens=2048)


def generate_intake_summary(division: str, intake_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate structured intake summary with recommendations."""
    prompt = (
        f"Division: {division.replace('_', ' ').title()}\n"
        f"Intake Data: {json.dumps(intake_data, indent=2)}\n\n"
        "Return a JSON object with these exact keys:\n"
        "- summary: string (2-3 sentence case overview)\n"
        "- priority: string ('high', 'medium', or 'low')\n"
        "- recommended_documents: array of document type strings\n"
        "- action_items: array of strings\n"
        "- flags: array of strings (concerns or issues to address)\n"
        "- estimated_timeline: string\n\n"
        "Return ONLY valid JSON, no markdown or explanation."
    )
    try:
        raw = complete(_BASE_SYSTEM, prompt, max_tokens=800)
        # Strip markdown code fences if present
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {
            "summary": "Intake received. Manual review required.",
            "priority": "medium",
            "recommended_documents": [],
            "action_items": ["Review intake data manually"],
            "flags": ["AI analysis unavailable"],
            "estimated_timeline": "TBD",
        }


def draft_follow_up_email(
    client_name: str,
    division: str,
    case_status: str,
    next_steps: List[str],
    staff_name: str = "Cruel & Associates Staff",
) -> Dict[str, str]:
    """Draft a follow-up email to a client."""
    steps_text = "\n".join(f"- {s}" for s in next_steps)
    prompt = (
        f"Client Name: {client_name}\n"
        f"Division: {division.replace('_', ' ').title()}\n"
        f"Case Status: {case_status}\n"
        f"Next Steps:\n{steps_text}\n"
        f"Staff Name: {staff_name}\n\n"
        "Draft a professional follow-up email. Return JSON with keys 'subject' and 'body'. "
        "The email should be warm, professional, and include the next steps clearly. "
        "Sign off as Cruel & Associates. Return ONLY valid JSON."
    )
    try:
        raw = complete(_BASE_SYSTEM, prompt, max_tokens=600)
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception:
        return {
            "subject": f"Update on Your {division.replace('_', ' ').title()} Case",
            "body": f"Dear {client_name},\n\nThank you for choosing Cruel & Associates. "
                    f"Your case is currently: {case_status}.\n\nNext steps:\n{steps_text}\n\n"
                    f"Please contact us with any questions.\n\nBest regards,\n{staff_name}\nCruel & Associates",
        }
