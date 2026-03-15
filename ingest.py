"""Ingest digest data into a local pipeline store."""

from __future__ import annotations

import argparse
from datetime import datetime

from main import collect_pipeline_snapshot
from pipeline_store import export_snapshot, load_snapshot, save_snapshot


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="Snapshot date to store (YYYY-MM-DD).")
    parser.add_argument(
        "--pipeline",
        default="weekly-digest",
        help="Logical pipeline name for stored snapshots.",
    )
    parser.add_argument(
        "--out-dir",
        help="Output directory for exported snapshot JSON.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-scrape even if a snapshot already exists for the date.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    target_date = args.run_date or datetime.now().strftime("%Y-%m-%d")
    existing = load_snapshot(pipeline=args.pipeline, run_date=target_date)

    if existing and not args.force:
        run_date = existing.get("date", target_date)
        print(f"  Snapshot for {run_date} already exists; skipping scrape.")
        export_path = export_snapshot(existing, out_dir=args.out_dir)
        print(f"  Re-exported snapshot: {export_path}")
        return

    snapshot = collect_pipeline_snapshot(out_dir=args.out_dir, run_date=target_date)
    run_key = save_snapshot(snapshot, pipeline=args.pipeline, overwrite=True)
    export_path = export_snapshot(snapshot, out_dir=args.out_dir)

    print(f"  Stored pipeline snapshot: {run_key}")
    print(f"  Exported pipeline snapshot: {export_path}")


if __name__ == "__main__":
    main()
