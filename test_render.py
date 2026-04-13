"""Quick test: scrape live data and render with the new Stitch template.
Bypasses pipeline_store (no psycopg2 needed).
"""
from main import collect_pipeline_snapshot, render_snapshot

print("Collecting live data (this takes 3-4 minutes)...")
snapshot = collect_pipeline_snapshot()
print("Rendering with new Stitch template...")
outputs = render_snapshot(snapshot)
print(f"\nDone! Open in browser:")
print(f"  {outputs['html']}")
