"""
Truthloom — synthetic validation dataset generator.

Creates *labeled* mini Android dumps and iOS backups so parsers can be
checked against known ground truth. Not real evidence.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class GroundTruthItem:
    artifact_type: str
    expected_summary_contains: str
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DatasetManifest:
    dataset_id: str
    kind: str
    path: str
    ground_truth: List[GroundTruthItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "kind": self.kind,
            "path": self.path,
            "ground_truth": [g.to_dict() for g in self.ground_truth],
            "notes": [
                "Synthetic data for parser validation only.",
                "Not a real device extract.",
            ],
        }


def _android_sms_db(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(
        """CREATE TABLE sms (
            _id INTEGER PRIMARY KEY,
            address TEXT,
            body TEXT,
            date INTEGER,
            type INTEGER
        )"""
    )
    conn.execute(
        "INSERT INTO sms (address, body, date, type) VALUES (?,?,?,?)",
        ("+15551234567", "Truthloom hello SMS", 1_700_000_000_000, 1),
    )
    conn.commit()
    conn.close()


def _android_accounts(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE accounts (name TEXT, type TEXT)")
    conn.execute(
        "INSERT INTO accounts VALUES (?, ?)",
        ("truthloom@example.com", "com.google"),
    )
    conn.commit()
    conn.close()


def generate_android_dump(out_dir: Path) -> DatasetManifest:
    out_dir = Path(out_dir)
    root = out_dir / "android_dump"
    root.mkdir(parents=True, exist_ok=True)
    _android_sms_db(root / "data" / "com.android.providers.telephony" / "databases" / "mmssms.db")
    _android_accounts(root / "system" / "users" / "0" / "accounts.db")
    (root / "misc" / "wifi").mkdir(parents=True, exist_ok=True)
    (root / "misc" / "wifi" / "WifiConfigStore.xml").write_text(
        '<string name="SSID">"TruthloomWifi"</string>\n',
        encoding="utf-8",
    )
    gt = [
        GroundTruthItem("android.sms", "Truthloom hello SMS"),
        GroundTruthItem("android.account", "truthloom@example.com"),
        GroundTruthItem("android.wifi_ssid", "TruthloomWifi"),
    ]
    return DatasetManifest(
        dataset_id="truthloom-android-v1",
        kind="android_folder_dump",
        path=str(root.resolve()),
        ground_truth=gt,
    )


def generate_ios_backup(out_dir: Path) -> DatasetManifest:
    out_dir = Path(out_dir)
    root = out_dir / "ios_backup"
    root.mkdir(parents=True, exist_ok=True)
    mconn = sqlite3.connect(str(root / "Manifest.db"))
    mconn.execute(
        "CREATE TABLE Files (fileID TEXT, domain TEXT, relativePath TEXT, flags INT)"
    )

    def add(domain: str, rel: str, payload: bytes) -> str:
        fid = hashlib.sha1(f"{domain}:{rel}".encode()).hexdigest()
        mconn.execute(
            "INSERT INTO Files VALUES (?,?,?,1)", (fid, domain, rel)
        )
        dest = root / fid[:2] / fid
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
        return fid

    # SMS-like for iDriller
    sms_path = out_dir / "_tmp_sms.db"
    c = sqlite3.connect(str(sms_path))
    c.execute(
        """CREATE TABLE message (
            ROWID INTEGER PRIMARY KEY, text TEXT, date INTEGER, is_from_me INTEGER, handle_id INTEGER
        )"""
    )
    c.execute(
        "CREATE TABLE handle (ROWID INTEGER PRIMARY KEY, id TEXT)"
    )
    c.execute("INSERT INTO handle VALUES (1, '+15559876543')")
    c.execute(
        "INSERT INTO message (text, date, is_from_me, handle_id) VALUES (?,?,?,?)",
        ("Truthloom iOS SMS", 700_000_000, 0, 1),
    )
    c.commit()
    c.close()
    add("HomeDomain", "Library/SMS/sms.db", sms_path.read_bytes())
    sms_path.unlink(missing_ok=True)

    # Notes for Recall Engine
    notes = out_dir / "_tmp_notes.db"
    c = sqlite3.connect(str(notes))
    c.execute(
        "CREATE TABLE ZICCLOUDSYNCINGOBJECT (ZTITLE TEXT, ZMODIFICATIONDATE1 REAL)"
    )
    c.execute(
        "INSERT INTO ZICCLOUDSYNCINGOBJECT VALUES (?, ?)",
        ("Truthloom Note", 700_000_100.0),
    )
    c.commit()
    c.close()
    add(
        "AppDomain-com.apple.Notes",
        "Library/Notes/NoteStore.sqlite",
        notes.read_bytes(),
    )
    notes.unlink(missing_ok=True)

    mconn.commit()
    mconn.close()

    # Minimal Manifest.plist unencrypted
    try:
        import plistlib

        with (root / "Manifest.plist").open("wb") as f:
            plistlib.dump({"IsEncrypted": False}, f)
        with (root / "Info.plist").open("wb") as f:
            plistlib.dump({"Device Name": "TruthloomPhone", "Product Version": "17.0"}, f)
    except Exception:
        pass

    gt = [
        GroundTruthItem("ios.sms", "Truthloom iOS SMS"),
        GroundTruthItem("ios.note", "Truthloom Note"),
    ]
    return DatasetManifest(
        dataset_id="truthloom-ios-v1",
        kind="ios_backup",
        path=str(root.resolve()),
        ground_truth=gt,
    )


def generate_all(out_dir: Path) -> List[DatasetManifest]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifests = [
        generate_android_dump(out_dir),
        generate_ios_backup(out_dir),
    ]
    index = {
        "tool": "Truthloom",
        "version": "1.0.0",
        "datasets": [m.to_dict() for m in manifests],
    }
    (out_dir / "truthloom_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    for m in manifests:
        (out_dir / f"{m.dataset_id}.json").write_text(
            json.dumps(m.to_dict(), indent=2), encoding="utf-8"
        )
    return manifests
