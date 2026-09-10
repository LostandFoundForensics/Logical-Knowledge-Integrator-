from memory_snare.parsers.accounts import AccountsParser
from memory_snare.parsers.browser import BrowserHistoryParser
from memory_snare.parsers.wifi import WifiConfigParser

__all__ = ["AccountsParser", "BrowserHistoryParser", "WifiConfigParser", "all_parsers"]


def all_parsers() -> list:
    return [AccountsParser(), BrowserHistoryParser(), WifiConfigParser()]
