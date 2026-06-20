from abc import ABC, abstractmethod


class BureauParser(ABC):
    """Base class for credit bureau PDF parsers."""

    @abstractmethod
    def can_parse(self, text: str) -> bool:
        """Return True if this parser can handle the given text."""

    @abstractmethod
    def extract_report_date(self, text: str) -> str:
        """Extract the report pull date."""

    @abstractmethod
    def extract_tradelines(self, text: str) -> list[dict]:
        """Extract list of tradeline dicts from raw text."""


def get_parser_for_bureau(bureau: str) -> "BureauParser":
    from app.parsers.experian import ExperianParser
    from app.parsers.equifax import EquifaxParser
    from app.parsers.transunion import TransUnionParser
    from app.parsers.innovis import InnovisParser

    parsers = {
        "experian": ExperianParser(),
        "equifax": EquifaxParser(),
        "transunion": TransUnionParser(),
        "innovis": InnovisParser(),
    }
    return parsers.get(bureau, ExperianParser())
