from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class HostTools:
    idevice_id: Optional[str] = None
    ideviceinfo: Optional[str] = None
    idevicepair: Optional[str] = None
    idevicebackup2: Optional[str] = None
    ideviceinstaller: Optional[str] = None
    notes: List[str] = field(default_factory=list)

    @property
    def any_available(self) -> bool:
        return any(
            [
                self.idevice_id,
                self.ideviceinfo,
                self.idevicepair,
                self.idevicebackup2,
            ]
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DeviceRef:
    udid: str
    name: str = ""
    product_type: str = ""
    product_version: str = ""
    paired: Optional[bool] = None
    raw: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
