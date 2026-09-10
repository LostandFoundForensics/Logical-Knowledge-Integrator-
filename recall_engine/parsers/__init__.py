from recall_engine.parsers.notes import NotesParser
from recall_engine.parsers.safari import SafariHistoryParser
from recall_engine.parsers.calendar import CalendarParser

__all__ = ["NotesParser", "SafariHistoryParser", "CalendarParser", "all_parsers"]


def all_parsers() -> list:
    return [NotesParser(), SafariHistoryParser(), CalendarParser()]
