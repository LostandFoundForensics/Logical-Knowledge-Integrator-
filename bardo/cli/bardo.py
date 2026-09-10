from __future__ import annotations
import json
import sys
from pathlib import Path

import typer

from bardo_artifact_store.storage_sqlite import BardoStore
from bardo_adapters.loki_modules.loki_adapter import (
    IDriverAdapter, AndroidExcavatorAdapter, RecallEngineAdapter,
)
from bardo_correlation.engine import EntityResolver, TemporalLinker
from bardo_timeline.timeline_builder import TimelineBuilder
from bardo_narrative.narrator import Narrator

app = typer.Typer(
    name="bardo",
    help="Bardo Engine — Cross-tool forensic correlation and narrative. Lost & Found Forensics.",
    add_completion=False,
)


@app.command()
def init(
    case_id: str = typer.Argument(..., help="Case ID (e.g., CASE-0001)"),
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Path for Bardo SQLite store"),
):
    """Initialize a Bardo case store."""
    store = BardoStore(db_path)
    summary = store.summary()
    typer.echo(f"Bardo case store initialized: {db_path}")
    typer.echo(f"  Entities: {summary['entities']}")
    typer.echo(f"  Artifacts: {summary['artifacts']}")
    typer.echo(f"  Events: {summary['events']}")
    typer.echo(f"  Relationships: {summary['relationships']}")


@app.command()
def ingest(
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Bardo store path"),
    idriller: Path = typer.Option(None, help="Path to iDriller evidence SQLite"),
    android: Path = typer.Option(None, help="Path to Android Excavator case SQLite"),
    recall: Path = typer.Option(None, help="Path to Recall Engine timeline JSON"),
):
    """Ingest tool outputs into Bardo."""
    store = BardoStore(db_path)

    if idriller:
        typer.echo(f"Ingesting iDriller: {idriller}")
        counts = IDriverAdapter().ingest(idriller, store)
        typer.echo(f"  → {counts}")

    if android:
        typer.echo(f"Ingesting Android Excavator: {android}")
        counts = AndroidExcavatorAdapter().ingest(android, store)
        typer.echo(f"  → {counts}")

    if recall:
        typer.echo(f"Ingesting Recall Engine: {recall}")
        counts = RecallEngineAdapter().ingest(recall, store)
        typer.echo(f"  → {counts}")

    summary = store.summary()
    typer.echo(f"\nStore totals: {summary}")
    store.close()


@app.command()
def correlate(
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Bardo store path"),
    out: Path = typer.Option(Path("./bardo_correlation.json"), help="Output path"),
):
    """Run entity resolution and temporal linking."""
    store = BardoStore(db_path)

    resolver = EntityResolver(store)
    matches = resolver.resolve_all()

    typer.echo(f"Entity resolution matches: {len(matches)}")
    for m in matches:
        typer.echo(f"  [{m.confidence:.2f}] {m.entity_a_id[:8]} ↔ {m.entity_b_id[:8]} — {m.match_basis}")

    result = {
        "entity_matches": [
            {
                "entity_a_id": m.entity_a_id,
                "entity_b_id": m.entity_b_id,
                "match_basis": m.match_basis,
                "confidence": m.confidence,
            }
            for m in matches
        ],
    }

    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    typer.echo(f"\nCorrelation results written to: {out}")
    store.close()


@app.command()
def timeline(
    case_id: str = typer.Argument(..., help="Case ID"),
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Bardo store path"),
    out: Path = typer.Option(Path("./bardo_timeline.json"), help="Output path"),
    min_confidence: float = typer.Option(0.0, help="Minimum confidence filter (0.0–1.0)"),
):
    """Build unified timeline from all ingested artifacts."""
    store = BardoStore(db_path)
    builder = TimelineBuilder(store)
    tl = builder.build(case_id=case_id, min_confidence=min_confidence)

    out.write_text(json.dumps(tl.to_dict(), indent=2), encoding="utf-8")
    typer.echo(
        f"Timeline built: {len(tl.entries)} entries "
        f"({tl.total_conflicts} conflicts) → {out}"
    )
    store.close()


@app.command()
def narrate(
    case_id: str = typer.Argument(..., help="Case ID"),
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Bardo store path"),
    out: Path = typer.Option(Path("./bardo_narrative.json"), help="Output JSON path"),
    text_out: Path = typer.Option(Path("./bardo_narrative.txt"), help="Output plain text path"),
):
    """Generate plain-language narrative from timeline."""
    store = BardoStore(db_path)
    builder = TimelineBuilder(store)
    tl = builder.build(case_id=case_id)

    narrator = Narrator()
    narrative = narrator.build_narrative(tl)

    violations = narrator.lint_narrative(narrative)
    if violations:
        typer.echo("⚠ Narrative lint violations:")
        for v in violations:
            typer.echo(f"  - {v}")

    out.write_text(json.dumps(narrative.to_dict(), indent=2), encoding="utf-8")
    text_out.write_text(narrative.full_text(), encoding="utf-8")
    typer.echo(f"Narrative written → {out}")
    typer.echo(f"Plain text → {text_out}")
    store.close()


@app.command()
def summary(
    db_path: Path = typer.Option(Path("./bardo_case.sqlite"), help="Bardo store path"),
):
    """Print a summary of what's in the Bardo store."""
    store = BardoStore(db_path)
    s = store.summary()
    typer.echo("Bardo Store Summary:")
    for k, v in s.items():
        typer.echo(f"  {k}: {v}")
    store.close()


if __name__ == "__main__":
    app()
