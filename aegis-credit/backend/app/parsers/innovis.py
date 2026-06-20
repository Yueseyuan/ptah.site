import re
from app.parsers.base import BureauParser
from app.services.ai_service import extract_tradelines_from_text


class InnovisParser(BureauParser):
    def can_parse(self, text: str) -> bool:
        return "innovis" in text.lower()

    def extract_report_date(self, text: str) -> str:
        match = re.search(r"(\d{1,2}/\d{1,2}/\d{4})", text)
        return match.group(1) if match else ""

    def extract_tradelines(self, text: str) -> list[dict]:
        tradelines = extract_tradelines_from_text(text)
        for tl in tradelines:
            tl["bureau"] = "innovis"
        return tradelines
