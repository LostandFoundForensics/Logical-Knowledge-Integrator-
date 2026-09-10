"""Artifact parsers — each has a plain-language label and parse(folder) method."""
from android_excavator.parsers.base import Parser, ParserInfo
from android_excavator.parsers.sms import SmsParser
from android_excavator.parsers.contacts import ContactsParser
from android_excavator.parsers.calls import CallLogParser
from android_excavator.parsers.chrome import ChromeHistoryParser

__all__ = [
    "Parser",
    "ParserInfo",
    "SmsParser",
    "ContactsParser",
    "CallLogParser",
    "ChromeHistoryParser",
    "all_parsers",
]


def all_parsers() -> list:
    return [
        SmsParser(),
        ContactsParser(),
        CallLogParser(),
        ChromeHistoryParser(),
    ]
