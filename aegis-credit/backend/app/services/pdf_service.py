import pdfplumber
import os


def extract_text_from_pdf(file_path: str) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"PDF not found: {file_path}")
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def detect_bureau_from_text(text: str) -> str:
    """Attempt to identify the credit bureau from report text.
    Returns 'all' when multiple bureaus are detected (combined/tri-merge report)."""
    text_lower = text.lower()
    found = []
    if "experian" in text_lower:
        found.append("experian")
    if "equifax" in text_lower:
        found.append("equifax")
    if "transunion" in text_lower or "trans union" in text_lower:
        found.append("transunion")
    if "innovis" in text_lower:
        found.append("innovis")
    if len(found) >= 2:
        return "all"
    return found[0] if found else "unknown"
