"""Theme-template library for demo sites.

Templates are category-aware theme packs that fill in a business profile. Output
is a single responsive HTML page under ~100KB (no inline images). A visible
banner reads 'Demo preview by [sender]' per the design brief.
"""
from __future__ import annotations

import html
from typing import Any

THEME_DESIGN = {
    "warm": {"bg": "#FAF6F2", "accent": "#B76E79", "ink": "#4A3B3B", "font": "Georgia, serif", "plate": "salonspa"},
    "bold": {"bg": "#F4F7FB", "accent": "#1F3D5C", "ink": "#202B36", "font": "'Helvetica Neue', Arial, sans-serif", "plate": "repair"},
    "fresh": {"bg": "#F5FAF6", "accent": "#3E8E5A", "ink": "#26332B", "font": "'Helvetica Neue', Arial, sans-serif", "plate": "cafe"},
    "elegant": {"bg": "#FDFAF4", "accent": "#7A5C88", "ink": "#3C2E44", "font": "Georgia, serif", "plate": "florist"},
}


def render_demo_site(profile: dict[str, Any], business: dict[str, Any], sender: str) -> str:
    """Render a complete demo page from profile + business info. Returns HTML string."""
    theme_key = (profile.get("brand") or {}).get("theme", "fresh")
    d = THEME_DESIGN.get(theme_key, THEME_DESIGN["fresh"])
    name = html.escape(business.get("name") or "Our Business")
    address = html.escape(business.get("address") or "")
    category = html.escape(business.get("category") or "local business")
    summary = html.escape(profile.get("summary") or "")
    services = profile.get("services") or []
    selling = profile.get("selling_points") or []
    tone = html.escape(profile.get("tone") or "friendly and professional")
    phone = html.escape(business.get("phone") or "")
    sender_h = html.escape(sender or "your demo partner")

    services_html = "".join(f"<li>{html.escape(s)}</li>" for s in services) or "<li>Contact us for details</li>"
    selling_html = "".join(f"<li>{html.escape(s)}</li>" for s in selling) or "<li>Proud to serve our local community</li>"

    contact_btn = f'<a class="btn" href="tel:{phone}">Call</a>' if phone else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — Demo preview</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family:{d['font']}; background:{d['bg']}; color:{d['ink']}; line-height:1.6; }}
  .banner {{ background:{d['accent']}; color:#fff; text-align:center; padding:8px 12px; font-size:13px; }}
  .banner a {{ color:#fff; }}
  header {{ padding:72px 24px 40px; text-align:center; }}
  header h1 {{ font-size:2.2rem; margin:0 0 8px; }}
  header p {{ font-size:1.05rem; opacity:.85; max-width:640px; margin:0 auto; }}
  section {{ max-width:900px; margin:0 auto; padding:32px 24px; }}
  h2 {{ color:{d['accent']}; font-size:1.5rem; }}
  ul {{ padding-left:20px; }}
  .btn {{ display:inline-block; background:{d['accent']}; color:#fff; padding:12px 22px; border-radius:6px;
          text-decoration:none; margin:6px 4px 0 0; }}
  .btn.ghost {{ background:transparent; color:{d['accent']}; border:2px solid {d['accent']}; }}
  footer {{ text-align:center; padding:32px 16px; font-size:.85rem; opacity:.75; border-top:1px solid rgba(0,0,0,.08); }}
  @media (max-width:600px) {{ header h1 {{ font-size:1.7rem; }} }}
</style>
</head>
<body>
<div class="banner">Demo preview by <a href="mailto:{sender_h}">{sender_h}</a> — this page is not yet live</div>
<header>
  <h1>{name}</h1>
  <p>{summary}</p>
  <p><em>{tone}</em> · {category}</p>
</header>
<section>
  <h2>Services</h2>
  <ul>{services_html}</ul>
</section>
<section>
  <h2>Why us</h2>
  <ul>{selling_html}</ul>
</section>
<section>
  <h2>Visit us</h2>
  <p>{address}</p>
  <p>{contact_btn}
     <a class="btn ghost" href="https://www.google.com/maps/search/?api=1&query={address.replace(' ','+')}">Directions</a></p>
</section>
<footer>Demo preview by {sender_h} — contact us to go live with a full website.</footer>
</body>
</html>
"""
