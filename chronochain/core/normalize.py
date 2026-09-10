"""
Time normalization helpers — original ChronoChain code.

Converts common mobile forensic time encodings into epoch milliseconds (UTC).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Union

# Apple Cocoa absolute time: seconds since 2001-01-01 UTC
APPLE_EPOCH_OFFSET_S = 978_307_200


def epoch_ms_to_iso(epoch_ms: int) -> str:
    """UTC ISO-8601. Returns em-dash for non-positive (synthetic) times."""
    try:
        v = int(epoch_ms)
        if v <= 0:
            return "—"
        dt = datetime.fromtimestamp(v / 1000.0, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    except Exception:
        return "—"


def parse_to_epoch_ms(
    value: Union[int, float, str, None],
    *,
    encoding: str = "unix_s",
) -> Optional[int]:
    """
    encoding:
      unix_s | unix_ms | unix_us | unix_ns
      apple_absolute   (seconds since 2001)
      apple_absolute_ns
      iso8601
    """
    if value is None or value == "":
        return None
    try:
        if encoding == "iso8601":
            s = str(value).strip().replace("Z", "+00:00")
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp() * 1000)

        num = float(value)
        if encoding == "unix_s":
            return int(num * 1000)
        if encoding == "unix_ms":
            return int(num)
        if encoding == "unix_us":
            return int(num / 1000)
        if encoding == "unix_ns":
            return int(num / 1_000_000)
        if encoding == "apple_absolute":
            return int((num + APPLE_EPOCH_OFFSET_S) * 1000)
        if encoding == "apple_absolute_ns":
            return int(num / 1_000_000) + APPLE_EPOCH_OFFSET_S * 1000
    except Exception:
        return None
    return None
