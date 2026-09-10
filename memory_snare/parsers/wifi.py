"""
Wi-Fi configuration hints from common dump locations (read-only text/XML).

Does not crack PSK material for use — only records that network names / fields
appear in the extract. Treat secrets as sensitive.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List

from memory_snare.core.discover import find_named, find_path_contains
from memory_snare.core.models import ArtifactHit
from memory_snare.parsers.base import Parser, ParserInfo

_SSID_RE = re.compile(
    r'(?:ssid|SSID)\s*[=":]\s*"?([^"\n<>{]+)"?',
    re.IGNORECASE,
)
_SSID_XML_RE = re.compile(
    r'name\s*=\s*"SSID"\s*>\s*"?([^"<]+)"?',
    re.IGNORECASE,
)


class WifiConfigParser(Parser):
    info = ParserInfo(
        parser_id="wifi",
        label="Wi-Fi network names",
        description="Finds SSID-like fields in WifiConfigStore / supplicant conf files.",
    )

    def parse(self, root: Path, *, limit: int = 20_000) -> List[ArtifactHit]:
        paths = find_named(
            root,
            (
                "WifiConfigStore.xml",
                "WifiConfigStore.yml",
                "wpa_supplicant.conf",
            ),
        )
        paths += find_path_contains(root, "WifiConfigStore")
        paths += find_path_contains(root, "wpa_supplicant")
        seen = set()
        hits: List[ArtifactHit] = []
        for p in paths:
            if not p.is_file():
                continue
            rp = p.resolve()
            if rp in seen:
                continue
            seen.add(rp)
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            ssids = []
            for m in list(_SSID_RE.finditer(text)) + list(_SSID_XML_RE.finditer(text)):
                ssid = m.group(1).strip().strip('"')
                if ssid and len(ssid) <= 64:
                    ssids.append(ssid)
            for ssid in dict.fromkeys(ssids):  # unique, order preserved
                hits.append(
                    ArtifactHit(
                        artifact_type="android.wifi_ssid",
                        summary=ssid,
                        record={"ssid": ssid},
                        source_path=str(p),
                        confidence=0.75,
                        flags=["ssid_pattern_match"],
                    )
                )
                if len(hits) >= limit:
                    return hits
        return hits
