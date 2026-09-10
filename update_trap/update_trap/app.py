"""
Update Trap — app.py
Tkinter UI entry point. Phase 1 (snapshot/diff/export) + Phase 2 (scope
picker: source profile, targets, structured-key kinds, manual include/
exclude patterns) + Phase 3 (parser breakage assessment, signature
advisory, dashboard, and exhibit pack generation) are all wired in here.

Window is taller than the original Phase 1 layout to make room for the
scope picker controls without overlapping the status box.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox

from update_trap.core.logbook import LogBook
from update_trap.core.models import Snapshot, SnapshotScope
from update_trap.core.snapshot import SnapshotBuilder
from update_trap.core.diff_engine import DiffEngine
from update_trap.core.export import Exporter
from update_trap.ui_bw import apply_bw_theme


class UpdateTrapApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Update Trap — Zero-Day OTA Diff Engine (LoKi)")
        self.geometry("800x720")
        self.resizable(False, False)
        apply_bw_theme(self)

        self.logbook = LogBook()
        self.baseline: Snapshot | None = None
        self.newsnap: Snapshot | None = None
        self._last_report = None
        self._last_bundle_dir: str | None = None

        self._build_ui()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        header = tk.Label(self, text="Update Trap", font=("Segoe UI", 22, "bold"), anchor="w")
        header.place(x=24, y=18, width=750, height=34)

        subtitle = tk.Label(
            self,
            text="Compare two snapshots to detect OTA/app/OS artifact path, schema, and structured-key changes.",
            font=("Segoe UI", 10),
            anchor="w",
        )
        subtitle.place(x=24, y=56, width=750, height=22)

        self._build_scope_picker()
        self._build_action_buttons()

        # Status box (pushed down to make room for the scope picker)
        self.status = tk.Text(self, wrap="word")
        self.status.place(x=24, y=470, width=750, height=210)
        self.status.insert("end", "Nothing has run. Set scope, then choose Baseline and New snapshot actions.\n")
        self.status.configure(state="disabled")

        footer = tk.Label(
            self,
            text="Read-only by default. Outputs are observed vs inferred. Investigator triggers every action.",
            font=("Segoe UI", 9),
            anchor="w",
        )
        footer.place(x=24, y=444, width=750, height=18)

    def _build_scope_picker(self) -> None:
        """Phase 2: source profile, targets, structured-key kinds, manual patterns."""
        tk.Label(self, text="Source Profile:", anchor="w").place(x=24, y=88, width=120, height=20)
        self.profile_var = tk.StringVar(value="Android Extraction")
        tk.OptionMenu(
            self, self.profile_var,
            "Android Extraction", "iOS Backup", "Mounted Image", "Generic Folder",
        ).place(x=150, y=84, width=200, height=28)

        tk.Label(self, text="Targets:", anchor="w").place(x=24, y=124, width=120, height=20)
        self.target_vars = {
            "accounts": tk.BooleanVar(value=True),
            "comms": tk.BooleanVar(value=True),
            "web": tk.BooleanVar(value=False),
            "media": tk.BooleanVar(value=False),
            "system": tk.BooleanVar(value=False),
            "apps": tk.BooleanVar(value=True),
        }
        tx, ty = 150, 122
        for i, (name, var) in enumerate(self.target_vars.items()):
            cb = tk.Checkbutton(self, text=name, variable=var)
            cb.place(x=tx + (i % 3) * 110, y=ty + (i // 3) * 24, width=100, height=22)

        tk.Label(self, text="Structured-key diff:", anchor="w").place(x=24, y=178, width=140, height=20)
        self.struct_vars = {
            "json": tk.BooleanVar(value=True),
            "plist": tk.BooleanVar(value=True),
            "xml": tk.BooleanVar(value=False),
        }
        sx, sy = 180, 176
        for i, (name, var) in enumerate(self.struct_vars.items()):
            cb = tk.Checkbutton(self, text=name, variable=var)
            cb.place(x=sx + i * 110, y=sy, width=100, height=22)

        tk.Label(self, text="Include patterns (optional):", anchor="w").place(x=24, y=210, width=200, height=20)
        self.include_text = tk.Text(self, wrap="none")
        self.include_text.place(x=24, y=232, width=360, height=56)

        tk.Label(self, text="Exclude patterns (optional):", anchor="w").place(x=410, y=210, width=200, height=20)
        self.exclude_text = tk.Text(self, wrap="none")
        self.exclude_text.place(x=410, y=232, width=360, height=56)

    def _build_action_buttons(self) -> None:
        btn_specs = [
            ("Create Baseline Snapshot…", self.create_baseline),
            ("Load Baseline Snapshot…", self.load_baseline),
            ("Create New Snapshot…", self.create_new),
            ("Load New Snapshot…", self.load_new),
            ("Run Diff (Explain Changes)", self.run_diff),
            ("Export Claim Pack…", self.export_claim_pack),
            ("Run Parser Breakage Check…", self.run_breakage_check),
            ("Generate Exhibit Pack…", self.generate_exhibits),
        ]

        x, y = 24, 300
        w, h = 360, 36
        gap_y = 8

        for i, (label, cmd) in enumerate(btn_specs):
            bx = x + (i % 2) * (w + 26)
            by = y + (i // 2) * (h + gap_y)
            b = tk.Button(self, text=label, command=cmd)
            b.place(x=bx, y=by, width=w, height=h)

    # ── Status helpers ────────────────────────────────────────────────────────

    def _set_status(self, text: str) -> None:
        self.status.configure(state="normal")
        self.status.delete("1.0", "end")
        self.status.insert("end", text)
        self.status.configure(state="disabled")

    def _append_status(self, text: str) -> None:
        self.status.configure(state="normal")
        self.status.insert("end", text)
        self.status.see("end")
        self.status.configure(state="disabled")

    def _pick_folder(self, title: str) -> str | None:
        path = filedialog.askdirectory(title=title)
        return os.path.abspath(path) if path else None

    def _pick_file(self, title: str, types: list[tuple[str, str]]) -> str | None:
        path = filedialog.askopenfilename(title=title, filetypes=types)
        return os.path.abspath(path) if path else None

    # ── Scope reading (Phase 2) ──────────────────────────────────────────────

    def _read_scope(self) -> SnapshotScope:
        profile_map = {
            "Android Extraction": "android_extraction",
            "iOS Backup": "ios_backup",
            "Mounted Image": "mounted_image",
            "Generic Folder": "generic_folder",
        }
        source_profile = profile_map.get(self.profile_var.get(), "generic_folder")

        targets = [name for name, var in self.target_vars.items() if var.get()]
        structured = [name for name, var in self.struct_vars.items() if var.get()]

        include_patterns = [ln.strip() for ln in self.include_text.get("1.0", "end").splitlines() if ln.strip()]
        exclude_patterns = [ln.strip() for ln in self.exclude_text.get("1.0", "end").splitlines() if ln.strip()]

        return SnapshotScope(
            source_profile=source_profile,
            targets=targets,
            structured_key_diff=structured,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
        )

    # ── Snapshot actions ──────────────────────────────────────────────────────

    def create_baseline(self) -> None:
        folder = self._pick_folder("Select baseline snapshot root folder")
        if not folder:
            return

        self.logbook = LogBook()
        self.logbook.note("Investigator created BASELINE snapshot.")
        self.logbook.note(f"Baseline root: {folder}")

        scope = self._read_scope()
        self._set_status("Building baseline snapshot...\n")
        try:
            builder = SnapshotBuilder(self.logbook)
            self.baseline = builder.build(folder, label="baseline", scope=scope)
            self._append_status(
                f"Baseline built.\nFiles: {len(self.baseline.files)}\n"
                f"SQLite DBs: {len(self.baseline.sqlite_dbs)}\n"
                f"Structured files: {len(self.baseline.structured_files)}\n\n"
            )
            self._append_status("Tip: Save snapshots by exporting Claim Pack after diff.\n")
        except Exception as e:
            messagebox.showerror("Update Trap", f"Failed to build baseline snapshot:\n{e}")

    def create_new(self) -> None:
        folder = self._pick_folder("Select NEW snapshot root folder")
        if not folder:
            return

        self.logbook.note("Investigator created NEW snapshot.")
        self.logbook.note(f"New root: {folder}")

        scope = self._read_scope()
        self._set_status("Building new snapshot...\n")
        try:
            builder = SnapshotBuilder(self.logbook)
            self.newsnap = builder.build(folder, label="new", scope=scope)
            self._append_status(
                f"New snapshot built.\nFiles: {len(self.newsnap.files)}\n"
                f"SQLite DBs: {len(self.newsnap.sqlite_dbs)}\n"
                f"Structured files: {len(self.newsnap.structured_files)}\n"
            )
        except Exception as e:
            messagebox.showerror("Update Trap", f"Failed to build new snapshot:\n{e}")

    def load_baseline(self) -> None:
        path = self._pick_file("Load baseline snapshot JSON", [("Snapshot JSON", "*.snapshot.json"), ("JSON", "*.json")])
        if not path:
            return
        try:
            self.baseline = Snapshot.load(path)
            self._set_status(
                f"Loaded baseline snapshot:\n{path}\nFiles: {len(self.baseline.files)}\n"
                f"SQLite DBs: {len(self.baseline.sqlite_dbs)}\nStructured files: {len(self.baseline.structured_files)}\n"
            )
        except Exception as e:
            messagebox.showerror("Update Trap", f"Failed to load snapshot:\n{e}")

    def load_new(self) -> None:
        path = self._pick_file("Load new snapshot JSON", [("Snapshot JSON", "*.snapshot.json"), ("JSON", "*.json")])
        if not path:
            return
        try:
            self.newsnap = Snapshot.load(path)
            self._set_status(
                f"Loaded new snapshot:\n{path}\nFiles: {len(self.newsnap.files)}\n"
                f"SQLite DBs: {len(self.newsnap.sqlite_dbs)}\nStructured files: {len(self.newsnap.structured_files)}\n"
            )
        except Exception as e:
            messagebox.showerror("Update Trap", f"Failed to load snapshot:\n{e}")

    def run_diff(self) -> None:
        if not self.baseline or not self.newsnap:
            messagebox.showwarning("Update Trap", "You must load/create BOTH baseline and new snapshots first.")
            return

        self.logbook.note("Investigator initiated DIFF run.")
        self._set_status("Running diff...\n")

        try:
            engine = DiffEngine(self.logbook)
            report = engine.diff(self.baseline, self.newsnap)
            self._append_status("Diff complete.\n\n")
            self._append_status(report.human_summary() + "\n\n")
            self._last_report = report
        except Exception as e:
            messagebox.showerror("Update Trap", f"Diff failed:\n{e}")

    def export_claim_pack(self) -> None:
        report = self._last_report
        if not report:
            messagebox.showwarning("Update Trap", "Run a diff first. (This generates the report to export.)")
            return

        outdir = self._pick_folder("Choose output folder for Claim Pack")
        if not outdir:
            return

        try:
            exporter = Exporter(self.logbook)
            # registry_path/signatures_dir left as None here — the
            # standalone "Run Parser Breakage Check" button below
            # produces those files into the same bundle on demand,
            # so a plain export doesn't require them up front.
            bundle = exporter.export(outdir, self.baseline, self.newsnap, report)
            self._last_bundle_dir = bundle
            messagebox.showinfo("Update Trap", f"Export complete:\n{bundle}")
        except Exception as e:
            messagebox.showerror("Update Trap", f"Export failed:\n{e}")

    # ── Phase 3 actions ───────────────────────────────────────────────────────

    def run_breakage_check(self) -> None:
        if not self._last_bundle_dir:
            messagebox.showwarning(
                "Update Trap",
                "Export a Claim Pack first — the breakage check reads diff_report.json from the bundle.",
            )
            return

        registry_path = self._pick_file(
            "Select parser_registry.json", [("JSON", "*.json")]
        )
        if not registry_path:
            return

        signatures_dir = self._pick_folder("Select signatures folder (optional — Cancel to skip)")

        try:
            import json
            from update_trap.core.breakage import ParserBreakageDetector
            from update_trap.core.signatures import SignatureLibrary
            from update_trap.core.claim_pack_importer import ClaimPackImporter
            from update_trap.core.dashboard import build_dashboard

            importer = ClaimPackImporter()
            payload = importer.load_claim_pack(self._last_bundle_dir)

            detector = ParserBreakageDetector(registry_path)
            breakage = detector.analyze(self._last_report)
            breakage_path = os.path.join(self._last_bundle_dir, "parser_breakage_assessment.json")
            with open(breakage_path, "w", encoding="utf-8") as f:
                json.dump([b.to_dict() for b in breakage], f, indent=2, sort_keys=True)

            advisory = []
            if signatures_dir:
                siglib = SignatureLibrary(signatures_dir)
                siglib.load()
                advisory = siglib.match(
                    self.baseline.scope.source_profile,
                    [pc.rel_path for pc in self._last_report.path_changes],
                )
                advisory_path = os.path.join(self._last_bundle_dir, "signature_advisory.json")
                with open(advisory_path, "w", encoding="utf-8") as f:
                    json.dump(advisory, f, indent=2, sort_keys=True)

            payload["breakage"] = [b.to_dict() for b in breakage]
            payload["advisory"] = advisory
            build_dashboard(self._last_bundle_dir, payload)

            self.logbook.note(
                f"Parser breakage check run: {len(breakage)} parser(s) flagged, "
                f"{len(advisory)} advisory signature match(es)."
            )
            self._append_status(
                f"\nParser breakage check complete.\n"
                f"Parsers flagged: {len(breakage)}\nAdvisory matches: {len(advisory)}\n"
            )
            messagebox.showinfo(
                "Update Trap",
                f"Breakage check complete.\n{len(breakage)} parser(s) flagged at risk.\nDashboard written to bundle.",
            )
        except Exception as e:
            messagebox.showerror("Update Trap", f"Breakage check failed:\n{e}")

    def generate_exhibits(self) -> None:
        if not self._last_bundle_dir:
            messagebox.showwarning("Update Trap", "Export a Claim Pack first.")
            return

        try:
            from update_trap.core.exhibits import generate_exhibit_pack
            exhibit_dir = generate_exhibit_pack(self._last_bundle_dir)
            self.logbook.note(f"Generated exhibit pack: {exhibit_dir}")
            messagebox.showinfo("Update Trap", f"Exhibit pack generated:\n{exhibit_dir}")
        except Exception as e:
            messagebox.showerror("Update Trap", f"Exhibit generation failed:\n{e}")


def main() -> None:
    app = UpdateTrapApp()
    app.mainloop()


if __name__ == "__main__":
    main()
