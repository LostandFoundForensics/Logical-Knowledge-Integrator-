from __future__ import annotations

from typing import Optional, Union

APPLE_EPOCH_OFFSET_S = 978_307_200


def apple_to_unix_ms(value: Union[int, float, None], *, unit: str = "seconds") -> Optional[int]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v == 0:
        return None
    scale = {
        "seconds": 1.0,
        "milliseconds": 1_000.0,
        "microseconds": 1_000_000.0,
        "nanoseconds": 1_000_000_000.0,
    }.get(unit)
    if not scale:
        return None
    unix_s = v / scale + APPLE_EPOCH_OFFSET_S
    if unix_s < 0:
        return None
    return int(unix_s * 1000)
