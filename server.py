"""Tiny server that serves the latest Shooter Digest HTML."""

import os
import re
import glob
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
NEIGHBORHOODS_FILE = os.path.join(BASE_DIR, "nyc-neighborhoods.html")
NYCGUY_FILE = os.path.join(BASE_DIR, "nycguy.html")

# ---------------------------------------------------------------------------
# Newsletter signup component
# ---------------------------------------------------------------------------
NEWSLETTER_SUBSCRIBE_EMAIL = os.environ.get(
    "NEWSLETTER_EMAIL", "newsletter@shooterdigest.com"
)

NEWSLETTER_HTML = """
<!-- ShooterDigest Newsletter Signup -->
<div class="sd-newsletter" id="sd-newsletter">
  <div class="sd-newsletter-inner">
    <div class="sd-newsletter-copy">
      <div class="sd-newsletter-heading">Get the weekly shooter intelligence brief in your inbox</div>
      <div class="sd-newsletter-sub">Free competitive analysis of the FPS market. Data, not hot takes.</div>
    </div>
    <form class="sd-newsletter-form" onsubmit="sdSubscribe(event)">
      <input
        class="sd-newsletter-input"
        type="email"
        placeholder="your@email.com"
        required
        id="sd-email-input"
        autocomplete="email"
      />
      <button class="sd-newsletter-btn" type="submit">Subscribe</button>
    </form>
    <div class="sd-newsletter-confirm" id="sd-confirm" style="display:none;">
      ✓ Check your inbox — one email away from being subscribed.
    </div>
  </div>
</div>
<style>
.sd-newsletter {
  background: #1b2838;
  border-top: 1px solid #2a475e;
  border-bottom: 1px solid #2a475e;
  padding: 2rem;
  margin: 2rem -2rem;
}
.sd-newsletter-inner {
  max-width: 680px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.sd-newsletter-heading {
  color: #e5e5e5;
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1.4;
}
.sd-newsletter-sub {
  color: #8f98a0;
  font-size: 0.85rem;
  margin-top: 0.2rem;
}
.sd-newsletter-form {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.sd-newsletter-input {
  flex: 1;
  min-width: 200px;
  background: #0f1923;
  border: 1px solid #2a475e;
  border-radius: 5px;
  color: #c7d5e0;
  font-size: 0.9rem;
  padding: 0.6rem 0.85rem;
  outline: none;
  transition: border-color 0.15s;
}
.sd-newsletter-input:focus {
  border-color: #f97316;
}
.sd-newsletter-input::placeholder {
  color: #4a5568;
}
.sd-newsletter-btn {
  background: #f97316;
  color: #fff;
  border: none;
  border-radius: 5px;
  font-size: 0.88rem;
  font-weight: 600;
  padding: 0.6rem 1.2rem;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, transform 0.1s;
}
.sd-newsletter-btn:hover {
  background: #ea6f0f;
}
.sd-newsletter-btn:active {
  transform: scale(0.97);
}
.sd-newsletter-confirm {
  color: #4ade80;
  font-size: 0.85rem;
  margin-top: 0.25rem;
}
@media (max-width: 560px) {
  .sd-newsletter {
    margin: 2rem -1rem;
    padding: 1.5rem 1rem;
  }
  .sd-newsletter-form {
    flex-direction: column;
  }
  .sd-newsletter-btn {
    width: 100%;
  }
}
</style>
<script>
function sdSubscribe(e) {
  e.preventDefault();
  var email = document.getElementById('sd-email-input').value;
  var subject = encodeURIComponent('Subscribe: ShooterDigest Newsletter');
  var body = encodeURIComponent('Hi,\\n\\nPlease add ' + email + ' to the ShooterDigest weekly newsletter.\\n\\nThanks!');
  window.location.href = 'mailto:NEWSLETTER_SUBSCRIBE_EMAIL?subject=' + subject + '&body=' + body;
  document.getElementById('sd-newsletter-form') && (document.querySelector('.sd-newsletter-form').style.display = 'none');
  document.getElementById('sd-confirm').style.display = 'block';
}
</script>
<!-- End ShooterDigest Newsletter Signup -->
""".replace("NEWSLETTER_SUBSCRIBE_EMAIL", NEWSLETTER_SUBSCRIBE_EMAIL)


OG_META_HTML = """
  <meta property="og:type" content="website" />
  <meta property="og:url" content="https://shooter.michaelpyon.com" />
  <meta property="og:title" content="ShooterDigest — Weekly Competitive Shooter Intelligence" />
  <meta property="og:description" content="SteamDB shows you the numbers. ShooterDigest tells you what they mean. Weekly analysis of the PC competitive FPS market." />
  <meta property="og:image" content="https://shooter.michaelpyon.com/og.png" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="ShooterDigest — Weekly Shooter Intelligence" />
  <meta name="twitter:description" content="Weekly analysis of the PC competitive FPS market. Data, not hot takes." />
  <meta name="twitter:image" content="https://shooter.michaelpyon.com/og.png" />
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🎯</text></svg>">
"""


def _strip_activeplayer_link(html: str) -> str:
    """Remove activeplayer.io link from old digest HTML."""
    return re.sub(
        r'For off-Steam audience estimates, see <a[^>]*>activeplayer\.io</a>\.',
        'Off-Steam audience estimates are not included in this digest.',
        html,
    )


def _inject_og_tags(html: str) -> str:
    """Inject OG meta tags into any digest HTML that doesn't already have them."""
    if 'og:title' in html:
        return html  # Already has OG tags, skip
    # Inject after the viewport meta tag
    injected = re.sub(
        r'(<meta name="viewport"[^>]*>)',
        r'\1' + OG_META_HTML,
        html,
        count=1,
    )
    if injected == html:
        # Fallback: inject before </head>
        injected = html.replace("</head>", OG_META_HTML + "</head>", 1)
    return injected


def _inject_newsletter_into_digest(html: str) -> str:
    """Inject the newsletter signup before the footer div in a digest HTML."""
    # Try to inject before the .footer div
    injected = re.sub(
        r'(<div class="footer">)',
        NEWSLETTER_HTML + r"\1",
        html,
        count=1,
    )
    if injected == html:
        # Fallback: inject before </body>
        injected = html.replace("</body>", NEWSLETTER_HTML + "</body>", 1)
    return injected


class DigestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=OUTPUT_DIR, **kwargs)

    def end_headers(self):
        # Prevent aggressive caching so new deploys are seen immediately
        self.send_header("Cache-Control", "no-cache, max-age=0")
        super().end_headers()

    def do_GET(self):
        # Health check
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
            return

        # Digest archive index
        if self.path in ("/digests", "/digests/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self._build_index_page().encode("utf-8"))
            return

        # Serve the NYC guy diagnostic
        if self.path in ("/nyc", "/nyc/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(NYCGUY_FILE, "rb") as f:
                self.wfile.write(f.read())
            return

        # Serve the NYC neighborhood ranker
        if self.path in ("/neighborhoods", "/neighborhoods/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(NEIGHBORHOODS_FILE, "rb") as f:
                self.wfile.write(f.read())
            return

        # Serve digest HTML files with newsletter injection
        if self.path == "/" or self.path == "/index.html":
            files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html")))
            if files:
                self.path = "/" + os.path.basename(files[-1])

        if self.path.startswith("/digest_") and self.path.endswith(".html"):
            filepath = os.path.join(OUTPUT_DIR, self.path.lstrip("/"))
            if os.path.isfile(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as fh:
                        content = fh.read()
                    content = _strip_activeplayer_link(content)
                    content = _inject_og_tags(content)
                    content = _inject_newsletter_into_digest(content)
                    encoded = content.encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(encoded)))
                    self.end_headers()
                    self.wfile.write(encoded)
                    return
                except Exception:
                    pass  # fall through to default handler

        # Serve OG image
        if self.path == "/og.png":
            og_path = os.path.join(BASE_DIR, "og.png")
            if os.path.isfile(og_path):
                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                with open(og_path, "rb") as f:
                    data = f.read()
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        super().do_GET()

    def _build_index_page(self) -> str:
        files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "digest_*.html")), reverse=True)
        if not files:
            return "<html><body><h1>No digests yet.</h1></body></html>"

        # Stats bar values
        digest_count = len(files)
        earliest_name = os.path.basename(files[-1])  # files sorted newest-first
        earliest_date_str = earliest_name.replace("digest_", "").replace(".html", "")
        try:
            since_str = datetime.strptime(earliest_date_str, "%Y-%m-%d").strftime("%B %Y")
        except ValueError:
            since_str = earliest_date_str

        # Build digest cards
        cards = []
        for f in files:
            name = os.path.basename(f)
            date_str = name.replace("digest_", "").replace(".html", "")
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                formatted_date = dt.strftime("Week of %B %-d, %Y")
            except ValueError:
                formatted_date = date_str

            teaser = self._extract_teaser(f)
            cards.append(f"""
  <div class="digest-card">
    <div class="digest-date">{formatted_date}</div>
    <div class="digest-teaser">{teaser}</div>
    <a class="digest-link" href="/{name}">→ Read digest</a>
  </div>""")

        items = "\n".join(cards)
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="Weekly FPS intelligence digest — Steam concurrents, Reddit sentiment, press coverage">
<title>ShooterDigest — Archive</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #0f1923; color: #c7d5e0; max-width: 640px; margin: 60px auto; padding: 0 20px; }}
  .about-section {{ padding-bottom: 2rem; margin-bottom: 2rem; border-bottom: 1px solid #2a475e; }}
  .about-title {{ color: #66c0f4; font-size: 2rem; font-weight: 700; margin-bottom: 0.4rem; }}
  .about-subtitle {{ color: #8f98a0; font-size: 0.95rem; line-height: 1.6; margin-bottom: 0.75rem; }}
  .stats-bar {{ color: #4a5568; font-size: 0.78rem; letter-spacing: 0.01em; }}
  .digests-section h2 {{ color: #8f98a0; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; }}
  .digest-card {{ padding: 1rem 0; border-bottom: 1px solid #1b2838; }}
  .digest-card:last-child {{ border-bottom: none; }}
  .digest-date {{ color: #c7d5e0; font-size: 0.95rem; font-weight: 600; margin-bottom: 0.2rem; }}
  .digest-teaser {{ color: #6b7280; font-size: 0.82rem; line-height: 1.5; margin-bottom: 0.4rem; }}
  .digest-link {{ color: #66c0f4; font-size: 0.85rem; text-decoration: none; }}
  .digest-link:hover {{ text-decoration: underline; }}

  /* Newsletter signup */
  .newsletter-cta {{
    background: #1b2838;
    border: 1px solid #2a475e;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 2rem 0;
  }}
  .newsletter-heading {{
    color: #e5e5e5;
    font-size: 1rem;
    font-weight: 700;
    line-height: 1.4;
    margin-bottom: 0.3rem;
  }}
  .newsletter-sub {{
    color: #8f98a0;
    font-size: 0.82rem;
    margin-bottom: 1rem;
  }}
  .newsletter-form {{
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }}
  .newsletter-input {{
    flex: 1;
    min-width: 180px;
    background: #0f1923;
    border: 1px solid #2a475e;
    border-radius: 5px;
    color: #c7d5e0;
    font-size: 0.88rem;
    padding: 0.55rem 0.75rem;
    outline: none;
    transition: border-color 0.15s;
  }}
  .newsletter-input:focus {{ border-color: #f97316; }}
  .newsletter-input::placeholder {{ color: #4a5568; }}
  .newsletter-btn {{
    background: #f97316;
    color: #fff;
    border: none;
    border-radius: 5px;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.55rem 1.1rem;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s;
  }}
  .newsletter-btn:hover {{ background: #ea6f0f; }}
  .newsletter-confirm {{
    color: #4ade80;
    font-size: 0.82rem;
    margin-top: 0.5rem;
    display: none;
  }}
  @media (max-width: 480px) {{
    .newsletter-form {{ flex-direction: column; }}
    .newsletter-btn {{ width: 100%; }}
  }}
</style>
</head>
<body>
<div class="about-section">
  <div class="about-title">ShooterDigest</div>
  <div class="about-subtitle">Steam concurrents, Reddit sentiment, and press coverage for 16 competitive shooters. One digest, every Monday.</div>
  <div class="stats-bar">{digest_count} digests published &middot; 16 games tracked &middot; Since {since_str}</div>
</div>

<!-- Newsletter signup -->
<div class="newsletter-cta">
  <div class="newsletter-heading">Get the weekly shooter intelligence brief in your inbox</div>
  <div class="newsletter-sub">Free competitive analysis of the FPS market. Data, not hot takes.</div>
  <form class="newsletter-form" onsubmit="indexSubscribe(event)">
    <input class="newsletter-input" type="email" placeholder="your@email.com" required id="index-email" autocomplete="email" />
    <button class="newsletter-btn" type="submit">Subscribe</button>
  </form>
  <div class="newsletter-confirm" id="index-confirm">✓ Check your inbox — one email away from being subscribed.</div>
</div>
<script>
function indexSubscribe(e) {{
  e.preventDefault();
  var email = document.getElementById('index-email').value;
  var subject = encodeURIComponent('Subscribe: ShooterDigest Newsletter');
  var body = encodeURIComponent('Hi,\\n\\nPlease add ' + email + ' to the ShooterDigest weekly newsletter.\\n\\nThanks!');
  window.location.href = 'mailto:{NEWSLETTER_SUBSCRIBE_EMAIL}?subject=' + subject + '&body=' + body;
  e.target.style.display = 'none';
  document.getElementById('index-confirm').style.display = 'block';
}}
</script>

<div class="digests-section">
  <h2>Archive</h2>
  {items}
</div>
</body>
</html>"""

    def _extract_teaser(self, filepath: str) -> str:
        """Pull the first <li> text from a digest file as a one-line teaser."""
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                content = fh.read(40000)
            match = re.search(r"<li>(.*?)</li>", content, re.DOTALL)
            if match:
                text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
                return (text[:100] + "…") if len(text) > 100 else text
        except Exception:
            pass
        return "Steam concurrents, Reddit sentiment, press coverage."


if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", PORT), DigestHandler)
    print(f"Serving Shooter Digest on port {PORT}")
    print(f"  /              → latest digest")
    print(f"  /digests       → archive index")
    print(f"  /neighborhoods → NYC neighborhood ranker")
    print(f"  /nyc           → The Jawnz Diagnostic")
    server.serve_forever()
