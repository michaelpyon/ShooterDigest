"""Render digest artifacts from a stored pipeline snapshot."""

from __future__ import annotations

import argparse
import sys

from main import render_snapshot
from pipeline_store import (
    load_exported_snapshot,
    load_latest_exported_snapshot,
    load_latest_snapshot,
    load_snapshot,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="Snapshot date to render (YYYY-MM-DD).")
    parser.add_argument(
        "--pipeline",
        default="weekly-digest",
        help="Logical pipeline name for stored snapshots.",
    )
    parser.add_argument("--out-dir", help="Output directory for rendered artifacts.")
    parser.add_argument("--docs-dir", help="Docs directory for publishable HTML.")
    return parser


def _load_requested_snapshot(args) -> dict | None:
    if args.run_date:
        return load_snapshot(pipeline=args.pipeline, run_date=args.run_date) or load_exported_snapshot(
            args.run_date,
            out_dir=args.out_dir,
        )

    return load_latest_snapshot(pipeline=args.pipeline) or load_latest_exported_snapshot(
        out_dir=args.out_dir
    )


def main() -> None:
    args = _build_parser().parse_args()
    snapshot = _load_requested_snapshot(args)

    if snapshot is None:
        target = args.run_date or "latest"
        print(f"  No stored snapshot found for {target}. Run ingest.py first.", file=sys.stderr)
        raise SystemExit(1)

    outputs = render_snapshot(snapshot, out_dir=args.out_dir, docs_dir=args.docs_dir)
    print(f"  Rendered digest from stored snapshot dated {snapshot.get('date')}.")
    for label, path in outputs.items():
        print(f"  {label}: {path}")


if __name__ == "__main__":
    main()
