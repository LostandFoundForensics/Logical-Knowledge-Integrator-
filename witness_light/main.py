"""
Witness Light — main.py
Court-safe interpretive drafting UI.

Merged from original (fixes #2, #8) and enhanced version:
- PanedWindow resizable layout (enhanced)
- Keyboard shortcuts Ctrl+O/G/S/E (enhanced)
- Visual ✓/○ validation markers in artifact list (enhanced)
- Export gate: approved drafts only (enhanced)
- draft_history versioning captures edited text at approval (enhanced)
- save_draft() writes real JSON to disk (stub replaced)
- Flexible Limitation/Unknown approval check (fix #8)
- next() enum lookup with null guard (fix #2)
"""
from __future__ import annotations

import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import List, Optional

from engine import generate_phase2_draft
from exporters import export_docx, export_pdf, export_txt
from models import Draft, Intent, Purpose, SentenceClass, now_iso
from storage import audit, ensure_dirs, load_artifacts, load_case

APP_USER = os.getenv("WITNESS_LIGHT_USER", "Investigator")


class WitnessLightApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Witness Light — Court-Safe Drafting")
        self.configure(bg="#f8f9fa")
        self.geometry("1020x760")
        self.minsize(980, 680)

        ensure_dirs()

        self.case = None
        self.artifacts: List = []
        self.selected_artifacts: List = []
        self.draft: Optional[Draft] = None
        self.draft_history: List[str] = []

        self._build_ui()
        self._bind_shortcuts()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background="#f8f9fa", foreground="#212529")
        style.configure("TButton", padding=8)
        style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Warning.TLabel", foreground="#d9534f")

        top = ttk.Frame(self)
        top.pack(fill="x", padx=16, pady=12)
        ttk.Label(top, text="Witness Light", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            top,
            text="Read-only interpretive drafting  •  Court-safe  •  Investigator-reviewed only",
            font=("Segoe UI", 10),
        ).pack(anchor="w")

        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill="both", expand=True, padx=16, pady=8)

        left = ttk.Frame(main_pane, width=320)
        right = ttk.Frame(main_pane)
        main_pane.add(left, weight=1)
        main_pane.add(right, weight=4)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_left_panel(self, parent):
        ttk.Button(parent, text="Load Case JSON  (Ctrl+O)", command=self.load_case_ui).pack(fill="x", pady=(0, 4))
        ttk.Button(parent, text="Load Artifact Set JSON", command=self.load_artifacts_ui).pack(fill="x", pady=(0, 12))

        ttk.Label(parent, text="Purpose:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.purpose_cb = ttk.Combobox(parent, values=[p.value for p in Purpose], state="readonly")
        self.purpose_cb.pack(fill="x", pady=(0, 12))
        self.purpose_cb.set(Purpose.INTERNAL_REVIEW.value)

        ttk.Label(parent, text="Intent:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.intent_cb = ttk.Combobox(parent, values=[i.value for i in Intent], state="readonly")
        self.intent_cb.pack(fill="x", pady=(0, 12))
        self.intent_cb.set(Intent.EXPLAIN_ARTIFACTS.value)

        ttk.Label(parent, text="Available Artifacts:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(12, 2))
        self.art_list = tk.Listbox(parent, selectmode="extended", height=12, bg="white", fg="#212529")
        self.art_list.pack(fill="both", expand=True, pady=(0, 8))

        ttk.Button(parent, text="Generate Draft  (Ctrl+G)", command=self.generate_draft_ui).pack(fill="x", pady=4)
        ttk.Button(parent, text="Approve Draft", command=self.approve_draft_ui).pack(fill="x", pady=4)

        ttk.Separator(parent).pack(fill="x", pady=12)

        for fmt in ["TXT", "DOCX", "PDF"]:
            ttk.Button(
                parent,
                text=f"Export {fmt}",
                command=lambda f=fmt.lower(): self.export_ui(f),
            ).pack(fill="x", pady=2)

        ttk.Separator(parent).pack(fill="x", pady=12)
        ttk.Button(parent, text="Save Draft to Disk  (Ctrl+S)", command=self.save_draft).pack(fill="x", pady=2)

    def _build_right_panel(self, parent):
        ttk.Label(parent, text="Draft Preview (editable)", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.preview = tk.Text(
            parent, wrap="word", bg="#ffffff", fg="#212529",
            insertbackground="#212529", font=("Segoe UI", 10),
        )
        self.preview.pack(fill="both", expand=True, pady=(4, 8))
        ttk.Label(
            parent,
            text="⚠  Limitation and Unknown statements must be preserved. All drafts require final human review before export.",
            style="Warning.TLabel",
            font=("Segoe UI", 9),
        ).pack(anchor="w")

    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.load_case_ui())
        self.bind("<Control-g>", lambda e: self.generate_draft_ui())
        self.bind("<Control-s>", lambda e: self.save_draft())
        self.bind("<Control-e>", lambda e: self.export_ui("docx"))

    def load_case_ui(self):
        path = filedialog.askopenfilename(title="Select case.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            self.case = load_case(path)
            audit("case_loaded", self.case.case_id, APP_USER, {"path": path, "locked": self.case.locked})
            messagebox.showinfo("Case Loaded", f"Loaded: {self.case.case_name}\nLocked: {self.case.locked}")
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))

    def load_artifacts_ui(self):
        path = filedialog.askopenfilename(title="Select artifact_set.json", filetypes=[("JSON", "*.json")])
        if not path:
            return
        try:
            truthloom_dir = Path(path).parent / "truthloom_headers"
            self.artifacts = load_artifacts(path, str(truthloom_dir) if truthloom_dir.exists() else None)
            self.art_list.delete(0, tk.END)
            for a in self.artifacts:
                validated = getattr(a, "truthloom_header", None) is not None
                status = "✓ Validated" if validated else "○ Not validated"
                self.art_list.insert(tk.END, f"{a.artifact_id} | {getattr(a, 'source_tool', 'unknown')} | {status}")
            if self.case:
                audit("artifacts_loaded", self.case.case_id, APP_USER, {"path": path, "count": len(self.artifacts)})
        except Exception as e:
            messagebox.showerror("Load Failed", str(e))

    def _require_ready(self) -> List[int]:
        if not self.case:
            raise RuntimeError("No case loaded.")
        if not getattr(self.case, "locked", False):
            raise RuntimeError("Case must be locked before drafting.")
        sel = list(self.art_list.curselection())
        if not sel:
            raise RuntimeError("Select at least one artifact.")
        return sel

    def generate_draft_ui(self):
        try:
            sel = self._require_ready()
            self.selected_artifacts = [self.artifacts[i] for i in sel]

            purpose = next((p for p in Purpose if p.value == self.purpose_cb.get()), None)
            intent = next((i for i in Intent if i.value == self.intent_cb.get()), None)
            if not purpose or not intent:
                messagebox.showerror("Invalid Selection", "Please select valid Purpose and Intent.")
                return

            if not messagebox.askyesno(
                "Confirm Generation",
                f"Purpose: {purpose.value}\nIntent: {intent.value}\n\n"
                "Generate court-safe interpretive draft?\n\n"
                "This tool does NOT infer motive, intent, or guilt.",
            ):
                return

            self.draft = generate_phase2_draft(self.case.case_id, purpose, intent, self.selected_artifacts)
            audit("draft_generated", self.case.case_id, APP_USER,
                  {"purpose": purpose.value, "intent": intent.value, "artifact_count": len(sel)})
            self._update_preview()
            messagebox.showinfo("Draft Generated", "Review and edit the draft. Approve when ready.")

        except Exception as e:
            messagebox.showerror("Generation Failed", str(e))

    def _update_preview(self):
        self.preview.delete("1.0", tk.END)
        if self.draft:
            self.preview.insert(tk.END, self.draft.as_text())

    def approve_draft_ui(self):
        if not self.draft:
            messagebox.showerror("No Draft", "Generate a draft first.")
            return

        edited_text = self.preview.get("1.0", tk.END).strip()
        edited_lower = edited_text.lower()

        has_limitation = (
            any(p.sentence_class == SentenceClass.LIMITATION for p in self.draft.paragraphs)
            or any(phrase in edited_lower for phrase in ("limitation", "partial", "incomplete"))
        )
        has_unknown = (
            any(p.sentence_class == SentenceClass.UNKNOWN for p in self.draft.paragraphs)
            or any(phrase in edited_lower for phrase in (
                "unknown", "does not establish", "absence of", "cannot determine"
            ))
        )

        if not (has_limitation and has_unknown):
            if not messagebox.askyesno(
                "Warning — Missing Sections",
                "The draft appears to be missing clear Limitation or Unknown statements.\n\n"
                "Removing these increases legal risk.\n\nApprove anyway?",
            ):
                return

        self.draft_history.append(edited_text)
        self.draft.approved = True
        self.draft.approved_time_iso = now_iso()
        self.draft.approved_by = APP_USER

        audit("draft_approved", self.draft.case_id, APP_USER, {
            "approved_time": self.draft.approved_time_iso,
            "version": len(self.draft_history),
            "edited_from_generated": len(self.draft_history) > 0,
        })
        messagebox.showinfo("Approved", "Draft approved and audit-logged.")

    def save_draft(self):
        """
        Save current draft state to disk as JSON.
        Replaces the stub that showed 'saved (in-memory)' without writing anything.
        The saved file records the current preview text and all paragraph metadata.
        """
        if not self.draft:
            messagebox.showwarning("No Draft", "Nothing to save yet.")
            return

        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)

        current_text = self.preview.get("1.0", tk.END).strip()

        payload = {
            "schema": "witness_light.draft.v1",
            "saved_utc": now_iso(),
            "case_id": self.draft.case_id,
            "purpose": self.draft.purpose.value,
            "intent": self.draft.intent.value,
            "created_time_iso": self.draft.created_time_iso,
            "approved": self.draft.approved,
            "approved_time_iso": self.draft.approved_time_iso,
            "approved_by": self.draft.approved_by,
            "disclaimer": self.draft.disclaimer,
            "paragraphs": [
                {
                    "sentence_class": p.sentence_class.value,
                    "text": p.text,
                    "artifact_ids": p.artifact_ids,
                    "truthloom_dataset_ids": p.truthloom_dataset_ids,
                    "confidence": p.confidence,
                }
                for p in self.draft.paragraphs
            ],
            "current_preview_text": current_text,
            "edit_history_count": len(self.draft_history),
        }

        filename = f"draft_{self.draft.case_id}_{now_iso()[:10].replace('-', '')}.json"
        save_path = out_dir / filename

        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

        audit("draft_saved", self.draft.case_id, APP_USER,
              {"path": str(save_path), "approved": self.draft.approved})
        messagebox.showinfo("Saved", f"Draft saved to:\n{save_path}")

    def export_ui(self, kind: str):
        if not self.draft:
            messagebox.showerror("No Draft", "Generate a draft first.")
            return
        if not self.draft.approved:
            messagebox.showerror(
                "Export Blocked",
                "You must approve the draft before exporting.\nUse 'Approve Draft' first.",
            )
            return

        out_dir = Path("output")
        out_dir.mkdir(exist_ok=True)
        base = f"witness_light_{self.draft.case_id}_{now_iso()[:10]}"

        try:
            if kind == "txt":
                path = export_txt(self.draft, str(out_dir), base + ".txt")
            elif kind == "docx":
                path = export_docx(self.draft, str(out_dir), base + ".docx")
            elif kind == "pdf":
                path = export_pdf(self.draft, str(out_dir), base + ".pdf")
            else:
                messagebox.showerror("Export", f"Unknown format: {kind}")
                return

            audit("exported", self.draft.case_id, APP_USER, {"format": kind, "path": path})
            messagebox.showinfo("Export Successful", f"Saved to:\n{path}")

        except Exception as e:
            messagebox.showerror("Export Failed", str(e))


if __name__ == "__main__":
    WitnessLightApp().mainloop()
