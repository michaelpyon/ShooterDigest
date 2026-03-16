"""Render digest artifacts from a stored pipeline snapshot.

Renders HTML and stores it in Postgres (digest_html table) so the
server can serve it without filesystem writes.
"""

from __future__ import annotations

import argparse
import sys

import db
from main import render_snapshot
from pipeline_store import (
    load_latest_snapshot,
    load_snapshot,
    store_digest_html,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="Snapshot date to render (YYYY-MM-DD).")
    parser.add_argument(
        "--pipeline",
        default="weekly-digest",
        help="Logical pipeline name for stored snapshots.",
    )
    parser.add_argument("--out-dir", help="Output directory for rendered artifacts (local only).")
    parser.add_argument("--docs-dir", help="Docs directory for publishable HTML (local only).")
    return parser


def _load_requested_snapshot(args) -> dict | None:
    if args.run_date:
        return load_snapshot(pipeline=args.pipeline, run_date=args.run_date)
    return load_latest_snapshot(pipeline=args.pipeline)


def main() -> None:
    args = _build_parser().parse_args()

    db.init_db()

    snapshot = _load_requested_snapshot(args)

    if snapshot is None:
        target = args.run_date or "latest"
        print(f"  No stored snapshot found for {target}. Run ingest.py first.", file=sys.stderr)
        raise SystemExit(1)

    # render_snapshot still writes to local filesystem for backward compat
    outputs = render_snapshot(snapshot, out_dir=args.out_dir, docs_dir=args.docs_dir)
    print(f"  Rendered digest from stored snapshot dated {snapshot.get('date')}.")
    for label, path in outputs.items():
        print(f"  {label}: {path}")

    # Store the HTML in Postgres so the server can serve it
    html_path = outputs.get("html")
    if html_path:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        run_date = snapshot.get("date") or "unknown"
        store_digest_html(run_date, html)
        print(f"  Stored digest HTML in Postgres for {run_date}")


if __name__ == "__main__":
    main()
