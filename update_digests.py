#!/usr/bin/env python3
"""
ShooterDigest batch updater — Cycle 3
- Injects new CSS into old digests
- Adds sticky nav bar, brand h1, back-to-top
- Adds prev/next navigation to all digest pages
- Updates index.html with dynamic teasers (auto-parsed from digest files)
"""

import os
import re
from datetime import datetime

DOCS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
TEMPLATE_FILE = os.path.join(DOCS_DIR, "digest_2026-02-23.html")

# -------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------

def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def write(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Wrote {os.path.basename(path)}")


# -------------------------------------------------------------------------
# Extract new CSS from template
# -------------------------------------------------------------------------

def extract_new_css(template_html):
    """Return just the content between <style> and </style> (inclusive).
    Strips any previously injected DIGEST_NAV_CSS to ensure idempotency.
    """
    m = re.search(r'(<style>.*?</style>)', template_html, re.DOTALL)
    if not m:
        raise ValueError("Could not find <style> block in template")
    css = m.group(1)
    # Strip previously injected digest-nav CSS to avoid duplication on re-runs
    css = re.sub(r'\n\s*/\* Prev/Next digest navigation \*/.*?\.digest-nav-placeholder \{ display: block; \}',
                 '', css, flags=re.DOTALL)
    return css


# -------------------------------------------------------------------------
# Parse digest files
# -------------------------------------------------------------------------

def get_digest_files():
    """Return sorted list of (date_str, filename, full_path) for all digest_ files."""
    files = []
    for fname in os.listdir(DOCS_DIR):
        m = re.match(r'digest_(\d{4}-\d{2}-\d{2})\.html$', fname)
        if m:
            date_str = m.group(1)
            files.append((date_str, fname, os.path.join(DOCS_DIR, fname)))
    files.sort(key=lambda x: x[0])  # oldest first
    return files


def format_date_display(date_str):
    """Convert '2026-02-23' to 'February 23, 2026'."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%B %-d, %Y")


# -------------------------------------------------------------------------
# Parse top gainer/loser from a digest HTML file
# -------------------------------------------------------------------------

def parse_top_movers(html):
    """
    Parse the top gainer and top loser from the digest HTML.
    Returns (gainer_name, gainer_pct, loser_name, loser_pct).
    """
    gainer_name, gainer_pct = None, None
    loser_name, loser_pct = None, None

    # Strategy 1: parse exec summary bullets (most reliable)
    m = re.search(r'Biggest mover:\s*([^<\n]+?)\s+at\s+([+-][\d.]+)%\s+month', html)
    if m:
        gainer_name = m.group(1).strip()
        try:
            gainer_pct = float(m.group(2))
        except Exception:
            pass

    m = re.search(r'Steepest decline:\s*([^<\n]+?)\s+at\s+([+-][\d.]+)%\s+month', html)
    if m:
        loser_name = m.group(1).strip()
        try:
            loser_pct = float(m.group(2))
        except Exception:
            pass

    if gainer_name and loser_name:
        return gainer_name, gainer_pct, loser_name, loser_pct

    # Strategy 2: scan trend-badges to find max/min MoM
    pattern = re.compile(
        r'<h3>([^<]+?)\s*(?:<[^>]+>\s*)*<span class="trend-badge (up|down|flat|neutral)">'
        r'[^<]*?([+-]?[\d.]+)%\s*MoM</span>',
        re.DOTALL
    )
    movers = []
    for m in pattern.finditer(html):
        game_raw = m.group(1).strip()
        game_name = re.sub(r'\s+', ' ', game_raw).strip()
        direction = m.group(2)
        try:
            pct = float(m.group(3))
            if direction == 'down':
                pct = -abs(pct)
            movers.append((game_name, pct))
        except Exception:
            pass

    if movers:
        movers.sort(key=lambda x: x[1])
        loser_name, loser_pct = movers[0]
        gainer_name, gainer_pct = movers[-1]

    return gainer_name, gainer_pct, loser_name, loser_pct


# -------------------------------------------------------------------------
# Prev/next nav CSS
# -------------------------------------------------------------------------

DIGEST_NAV_CSS = """
    /* Prev/Next digest navigation */
    .digest-nav {
      display: flex; justify-content: space-between; align-items: center;
      margin: 3rem 0 1rem;
      padding: 1rem 0;
      border-top: 1px solid #2a475e;
    }
    .digest-nav-link {
      color: #66c0f4; text-decoration: none; font-size: 0.88rem;
      font-weight: 600; transition: color 0.15s;
      padding: 0.4rem 0;
    }
    .digest-nav-link:hover { color: #f97316; }
    .digest-nav-placeholder { display: block; }
"""


# -------------------------------------------------------------------------
# Prev/next nav HTML
# -------------------------------------------------------------------------

def make_digest_nav_html(prev_info, next_info):
    """
    Build prev/next bottom navigation HTML.
    prev_info / next_info: (date_str, filename) or None
    """
    if prev_info:
        prev_date, prev_fname = prev_info
        prev_label = format_date_display(prev_date)
        prev_link = f'<a href="{prev_fname}" class="digest-nav-link prev">&#8592; {prev_label}</a>'
    else:
        prev_link = '<span class="digest-nav-placeholder"></span>'

    if next_info:
        next_date, next_fname = next_info
        next_label = format_date_display(next_date)
        next_link = f'<a href="{next_fname}" class="digest-nav-link next">{next_label} &#8594;</a>'
    else:
        next_link = '<span class="digest-nav-placeholder"></span>'

    return f'\n  <div class="digest-nav">\n    {prev_link}\n    {next_link}\n  </div>'


# -------------------------------------------------------------------------
# Strip previously injected elements (idempotency)
# -------------------------------------------------------------------------

def strip_old_additions(html):
    """Remove previously injected elements so updates are idempotent."""
    # Remove old digest-nav divs
    html = re.sub(r'\s*<div class="digest-nav">.*?</div>', '', html, flags=re.DOTALL)
    # Remove old back-to-top anchor
    html = re.sub(r'\s*<a id="back-to-top"[^>]*>[^<]*</a>', '', html, flags=re.DOTALL)
    # Remove old btt inline script block
    html = re.sub(r'\s*<script>\s*//\s*Back-to-top.*?</script>', '', html, flags=re.DOTALL)
    return html


# -------------------------------------------------------------------------
# Back-to-top JS snippet
# -------------------------------------------------------------------------

BTT_SCRIPT = """
  <script>
  // Back-to-top button
  const _btt = document.getElementById('back-to-top');
  if (_btt) {
    window.addEventListener('scroll', () => {
      _btt.classList.toggle('visible', window.scrollY > 600);
    });
  }
  </script>"""

BTT_ANCHOR = '\n  <a id="back-to-top" href="#" class="back-to-top" onclick="window.scrollTo({top:0,behavior:\'smooth\'});return false;">&#8593; Top</a>'


# -------------------------------------------------------------------------
# Batch update old digests (Step 1)
# -------------------------------------------------------------------------

def update_old_digest(html, new_css_block, title_date_str, prev_info, next_info):
    """
    Given old digest HTML, return upgraded HTML with:
    - New CSS
    - Sticky nav bar
    - Brand h1
    - Back-to-top button + JS
    - Prev/next navigation
    """
    # 0. Strip any previously injected elements (idempotent)
    html = strip_old_additions(html)

    # 1. Replace CSS block; inject digest-nav CSS just before </style>
    extended_css = new_css_block[:-8] + DIGEST_NAV_CSS + "\n  </style>"
    # Use lambda to avoid backslash interpretation in replacement string
    html = re.sub(r'<style>.*?</style>', lambda _: extended_css, html, flags=re.DOTALL)

    # 2. Replace <body> opener + old h1 with nav + brand h1
    nav_html = (
        '<body>\n'
        '  <nav class="site-nav">\n'
        '    <a href="index.html" class="nav-back">&#8592; All Digests</a>\n'
        '    <a href="index.html" class="nav-logo">Shooter<span>Digest</span></a>\n'
        '  </nav>\n'
        '  <h1><span class="brand-shooter">Shooter</span><span class="brand-digest">Digest</span></h1>'
    )
    html = re.sub(r'<body>\s*<h1>Shooter Digest</h1>', nav_html, html)

    # 3. Add prev/next navigation + back-to-top anchor + scroll JS before </body>
    nav = make_digest_nav_html(prev_info, next_info)
    suffix = nav + BTT_ANCHOR + BTT_SCRIPT

    if '\n</body>' in html:
        html = html.replace('\n</body>', suffix + '\n</body>')
    elif '</body>' in html:
        html = html.replace('</body>', suffix + '\n</body>')

    return html


# -------------------------------------------------------------------------
# Update new digest (Step 2 only — add prev/next + nav CSS)
# -------------------------------------------------------------------------

def update_new_digest(html, prev_info, next_info):
    """
    For the already-updated new digest (2026-02-23), add prev/next navigation.
    The new digest already has the full CSS, nav bar, and back-to-top.
    We just need to add digest-nav CSS + prev/next links + re-add back-to-top.
    """
    # Strip old additions (idempotent)
    html = strip_old_additions(html)

    # Inject digest-nav CSS if missing
    if '.digest-nav' not in html:
        style_end = html.find('\n  </style>')
        if style_end != -1:
            html = (html[:style_end] + DIGEST_NAV_CSS
                    + '\n  </style>' + html[style_end + len('\n  </style>'):])

    # Re-add prev/next nav + back-to-top anchor (JS already in page from original)
    nav = make_digest_nav_html(prev_info, next_info)
    suffix = nav + BTT_ANCHOR

    if '\n</body>' in html:
        html = html.replace('\n</body>', suffix + '\n</body>')
    elif '</body>' in html:
        html = html.replace('</body>', suffix + '\n</body>')

    return html


# -------------------------------------------------------------------------
# Generate index.html dynamically (Step 3)
# -------------------------------------------------------------------------

def generate_index(digest_files):
    """
    Regenerate index.html with teasers parsed from digest files.
    digest_files: sorted oldest-first list of (date_str, fname, path)
    """
    items_html = ""
    for i, (date_str, fname, path) in enumerate(reversed(digest_files)):
        html = read(path)
        gainer_name, gainer_pct, loser_name, loser_pct = parse_top_movers(html)

        display_date = format_date_display(date_str)
        is_latest = (i == 0)  # first in reversed = newest

        badge = ' <span class="badge-new">Latest</span>' if is_latest else ''

        # Count game cards
        count = len(re.findall(r'<div class="card"', html)) or 15

        teaser_parts = [f"{count} games"]

        if gainer_name and gainer_pct is not None:
            pct_str = f"+{gainer_pct:.0f}%" if gainer_pct >= 0 else f"{gainer_pct:.0f}%"
            teaser_parts.append(f'<span class="t-up">&#9650; {gainer_name} {pct_str}</span>')

        if loser_name and loser_pct is not None:
            pct_str = f"{loser_pct:.0f}%"
            teaser_parts.append(f'<span class="t-down">&#9660; {loser_name} {pct_str}</span>')

        teaser_html = " &nbsp;&middot;&nbsp; ".join(teaser_parts)

        items_html += (
            f'      <li><a href="{fname}">'
            f'<span class="date">{display_date}{badge}'
            f'<span class="teaser">{teaser_html}</span></span>'
            f'<span class="arrow">&#8594;</span></a></li>\n'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ShooterDigest &mdash; Archive</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      background: #0f0f0f;
      color: #e8e8e8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh;
      padding: 60px 24px;
    }}

    .container {{
      max-width: 640px;
      margin: 0 auto;
    }}

    header {{
      margin-bottom: 48px;
    }}

    h1 {{
      font-size: 2rem;
      font-weight: 700;
      letter-spacing: -0.5px;
      color: #ffffff;
    }}

    h1 span {{
      color: #f97316;
    }}

    .subtitle {{
      margin-top: 8px;
      font-size: 0.9rem;
      color: #666;
    }}

    ul {{
      list-style: none;
    }}

    ul li {{
      border-bottom: 1px solid #1e1e1e;
    }}

    ul li:first-child {{
      border-top: 1px solid #1e1e1e;
    }}

    ul li a {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 14px 4px;
      color: #e8e8e8;
      text-decoration: none;
      font-size: 1rem;
      transition: color 0.15s;
    }}

    ul li a:hover {{
      color: #f97316;
    }}

    ul li a .date {{
      font-weight: 600;
    }}

    .teaser {{
      display: block;
      font-size: 0.72rem;
      font-weight: 400;
      color: #555;
      margin-top: 3px;
    }}

    .t-up {{ color: #4ade80; }}
    .t-down {{ color: #f87171; }}

    ul li a .arrow {{
      color: #444;
      font-size: 0.85rem;
      transition: color 0.15s, transform 0.15s;
    }}

    ul li a:hover .arrow {{
      color: #f97316;
      transform: translateX(4px);
    }}

    .badge-new {{
      font-size: 0.65rem;
      font-weight: 700;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      color: #f97316;
      border: 1px solid #f97316;
      border-radius: 4px;
      padding: 2px 6px;
      margin-left: 10px;
      vertical-align: middle;
    }}

    footer {{
      margin-top: 56px;
      font-size: 0.78rem;
      color: #444;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Shooter<span>Digest</span></h1>
      <p class="subtitle">Weekly competitive FPS briefings &mdash; sorted newest first</p>
    </header>

    <ul>
{items_html}    </ul>

    <footer>Auto-updated weekly &middot; <a href="https://github.com/michaelpyon/ShooterDigest" style="color:#555;text-decoration:none;">GitHub</a></footer>
  </div>
</body>
</html>
"""


# -------------------------------------------------------------------------
# Update main.py — inject generate_index function
# -------------------------------------------------------------------------

GENERATE_INDEX_FUNC = '''
# ---------------------------------------------------------------------------
# Index page generation
# ---------------------------------------------------------------------------

def generate_index(docs_dir: str) -> str:
    """
    Regenerate index.html by parsing all digest HTML files in docs_dir.
    Extracts top gainer/loser from each digest for the teaser line.
    """
    import re as _re
    from datetime import datetime as _dt

    def _fmt_date(date_str):
        dt = _dt.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%B %-d, %Y")

    def _parse_movers(html):
        gainer_name, gainer_pct, loser_name, loser_pct = None, None, None, None
        m = _re.search(r\'Biggest mover:\\s*([^<\\n]+?)\\s+at\\s+([+-][\\d.]+)%\\s+month\', html)
        if m:
            gainer_name = m.group(1).strip()
            try:
                gainer_pct = float(m.group(2))
            except Exception:
                pass
        m = _re.search(r\'Steepest decline:\\s*([^<\\n]+?)\\s+at\\s+([+-][\\d.]+)%\\s+month\', html)
        if m:
            loser_name = m.group(1).strip()
            try:
                loser_pct = float(m.group(2))
            except Exception:
                pass
        return gainer_name, gainer_pct, loser_name, loser_pct

    # Discover digest files
    files = []
    for fname in os.listdir(docs_dir):
        mm = _re.match(r\'digest_(\\d{4}-\\d{2}-\\d{2})\\.html$\', fname)
        if mm:
            files.append((mm.group(1), fname, os.path.join(docs_dir, fname)))
    files.sort(key=lambda x: x[0])

    # Build list items newest-first
    items_html = ""
    for i, (date_str, fname, path) in enumerate(reversed(files)):
        with open(path, "r", encoding="utf-8") as f:
            html = f.read()
        gainer_name, gainer_pct, loser_name, loser_pct = _parse_movers(html)

        display_date = _fmt_date(date_str)
        is_latest = (i == 0)
        badge = \' <span class="badge-new">Latest</span>\' if is_latest else \'\'

        count = len(_re.findall(r\'<div class="card"\', html)) or 15
        teaser_parts = [f"{count} games"]

        if gainer_name and gainer_pct is not None:
            pct_str = f"+{gainer_pct:.0f}%" if gainer_pct >= 0 else f"{gainer_pct:.0f}%"
            teaser_parts.append(f\'<span class="t-up">&#9650; {gainer_name} {pct_str}</span>\')
        if loser_name and loser_pct is not None:
            pct_str = f"{loser_pct:.0f}%"
            teaser_parts.append(f\'<span class="t-down">&#9660; {loser_name} {pct_str}</span>\')

        teaser_html = " &nbsp;&middot;&nbsp; ".join(teaser_parts)
        items_html += (
            f\'      <li><a href="{fname}">\'
            f\'<span class="date">{display_date}{badge}\'
            f\'<span class="teaser">{teaser_html}</span></span>\'
            f\'<span class="arrow">&#8594;</span></a></li>\\n\'
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ShooterDigest &mdash; Archive</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #0f0f0f; color: #e8e8e8;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      min-height: 100vh; padding: 60px 24px;
    }}
    .container {{ max-width: 640px; margin: 0 auto; }}
    header {{ margin-bottom: 48px; }}
    h1 {{ font-size: 2rem; font-weight: 700; letter-spacing: -0.5px; color: #ffffff; }}
    h1 span {{ color: #f97316; }}
    .subtitle {{ margin-top: 8px; font-size: 0.9rem; color: #666; }}
    ul {{ list-style: none; }}
    ul li {{ border-bottom: 1px solid #1e1e1e; }}
    ul li:first-child {{ border-top: 1px solid #1e1e1e; }}
    ul li a {{
      display: flex; align-items: center; justify-content: space-between;
      padding: 14px 4px; color: #e8e8e8; text-decoration: none;
      font-size: 1rem; transition: color 0.15s;
    }}
    ul li a:hover {{ color: #f97316; }}
    ul li a .date {{ font-weight: 600; }}
    .teaser {{ display: block; font-size: 0.72rem; font-weight: 400; color: #555; margin-top: 3px; }}
    .t-up {{ color: #4ade80; }}
    .t-down {{ color: #f87171; }}
    ul li a .arrow {{ color: #444; font-size: 0.85rem; transition: color 0.15s, transform 0.15s; }}
    ul li a:hover .arrow {{ color: #f97316; transform: translateX(4px); }}
    .badge-new {{
      font-size: 0.65rem; font-weight: 700; letter-spacing: 0.5px;
      text-transform: uppercase; color: #f97316; border: 1px solid #f97316;
      border-radius: 4px; padding: 2px 6px; margin-left: 10px; vertical-align: middle;
    }}
    footer {{ margin-top: 56px; font-size: 0.78rem; color: #444; }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Shooter<span>Digest</span></h1>
      <p class="subtitle">Weekly competitive FPS briefings &mdash; sorted newest first</p>
    </header>
    <ul>
{items_html}    </ul>
    <footer>Auto-updated weekly &middot; <a href="https://github.com/michaelpyon/ShooterDigest" style="color:#555;text-decoration:none;">GitHub</a></footer>
  </div>
</body>
</html>
"""
'''


def inject_generate_index(main_py_path):
    """Inject or replace generate_index function in main.py."""
    with open(main_py_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already injected
    if 'def generate_index(' in content:
        # Replace existing — use lambda to avoid backslash interpretation
        content = re.sub(
            r'\n# -{10,}\n# Index page generation\n# -{10,}\n\ndef generate_index\(.*?\n(?=\n# -{10,}|\ndef |\nif __name__)',
            lambda _: GENERATE_INDEX_FUNC,
            content,
            flags=re.DOTALL
        )
    else:
        # Inject before the main() function
        content = content.replace('\n# ---------------------------------------------------------------------------\n# Main\n# ---------------------------------------------------------------------------',
                                   GENERATE_INDEX_FUNC + '\n# ---------------------------------------------------------------------------\n# Main\n# ---------------------------------------------------------------------------')

    # Also update main() to write index.html
    INDEX_WRITE_CODE = '''
    # Write index.html
    docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    # Copy new digest to docs/ (optional step — usually done manually)
    index_path = os.path.join(docs_dir, "index.html")
    with open(index_path, "w") as f:
        f.write(generate_index(docs_dir))
    print(f"  Updated: {index_path}")
'''

    # Insert after the html_path write block (before _save_history)
    if 'generate_index' not in content or 'Updated: {index_path}' not in content:
        content = content.replace(
            "    # Save history\n    _save_history(results, out_dir)",
            INDEX_WRITE_CODE + "\n    # Save history\n    _save_history(results, out_dir)"
        )

    with open(main_py_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ Updated main.py with generate_index()")


# -------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------

def main():
    print("\n=== ShooterDigest Batch Updater — Cycle 3 ===\n")

    # Read template (Feb 23 — the updated digest)
    template_html = read(TEMPLATE_FILE)
    new_css_block = extract_new_css(template_html)
    print(f"  Extracted CSS ({len(new_css_block):,} chars) from template")

    # Get all digest files sorted oldest→newest
    digest_files = get_digest_files()
    print(f"  Found {len(digest_files)} digest files: {[d[1] for d in digest_files]}")

    # Update each digest
    for idx, (date_str, fname, path) in enumerate(digest_files):
        html = read(path)

        # Determine prev/next
        prev_info = None
        next_info = None
        if idx > 0:
            prev_date, prev_fname, _ = digest_files[idx - 1]
            prev_info = (prev_date, prev_fname)
        if idx < len(digest_files) - 1:
            next_date, next_fname, _ = digest_files[idx + 1]
            next_info = (next_date, next_fname)

        is_new = (fname == "digest_2026-02-23.html")

        if is_new:
            updated = update_new_digest(html, prev_info, next_info)
        else:
            updated = update_old_digest(html, new_css_block, date_str, prev_info, next_info)

        write(path, updated)

    # Regenerate index.html
    print("\n  Regenerating index.html...")
    index_html = generate_index(digest_files)
    write(os.path.join(DOCS_DIR, "index.html"), index_html)

    # Update main.py
    main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    print("\n  Updating main.py...")
    inject_generate_index(main_py)

    print("\n=== Done! All files updated. ===\n")


if __name__ == "__main__":
    main()
