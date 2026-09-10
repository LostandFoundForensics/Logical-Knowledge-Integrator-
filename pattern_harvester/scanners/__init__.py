from pattern_harvester.scanners.base import Scanner
from pattern_harvester.scanners.email_scan import EmailScanner
from pattern_harvester.scanners.phone_scan import PhoneScanner
from pattern_harvester.scanners.url_scan import UrlScanner
from pattern_harvester.scanners.ip_scan import IpScanner

__all__ = [
    "Scanner",
    "EmailScanner",
    "PhoneScanner",
    "UrlScanner",
    "IpScanner",
    "all_scanners",
]


def all_scanners() -> list:
    return [
        EmailScanner(),
        PhoneScanner(),
        UrlScanner(),
        IpScanner(),
    ]
