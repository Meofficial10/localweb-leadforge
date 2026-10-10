"""Theme-template library for demo sites (Workstream C).

8 theme packs (clinical/healthcare, salon/beauty, cafe/food, boutique/retail,
repair/trades, education/tuition, fitness/gym, generic) — each with its own
palette, system-font stack, hero style and inline SVG icon set. No external
fonts, scripts, embeds or tracking; single responsive mobile-first page under
~100KB; robots noindex. Services/Why-choose sections only render verified or
generic content, otherwise a clearly-labelled Sample content block (per B).
"""
from __future__ import annotations

import html
import re
from typing import Any

CATEGORY_THEMES: list[tuple[tuple[str, ...], str]] = [
    (("dent", "clinic", "medical", "health", "doctor", "pharmacy", "dental", "ortho", "optometr"), "clinical"),
    (("salon", "spa", "beauty", "barber", "nails", "lash", "aesthetic", "hair"), "salon"),
    (("cafe", "bakery", "restaurant", "food", "bistro", "coffee", "juice", "kitchen"), "cafe"),
    (("boutique", "retail", "shop", "store", "florist", "gift", "fashion", "jewel"), "boutique"),
    (("repair", "trade", "plumb", "auto", "electric", "workshop", "handyman", "roof", "mechanic"), "repair"),
    (("tuition", "education", "school", "tutor", "learning", "training", "academy", "kindergarten"), "education"),
    (("gym", "fitness", "yoga", "pilates", "martial", "training", "exercise", "sports"), "fitness"),
]

THEMES: dict[str, dict[str, Any]] = {
    "clinical": {
        "bg": "#F6F8FB", "surface": "#FFFFFF", "accent": "#1F6FB2", "accent2": "#2F9E8D",
        "ink": "#16283C", "muted": "#5A6B7B", "hero": "light", "radius": "12px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "salon": {
        "bg": "#FBF6F4", "surface": "#FFFFFF", "accent": "#B76E79", "accent2": "#8E5B76",
        "ink": "#4A3B3B", "muted": "#8A7272", "hero": "soft", "radius": "14px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "cafe": {
        "bg": "#FAF6EF", "surface": "#FFFFFF", "accent": "#B3772E", "accent2": "#6E8B3E",
        "ink": "#3D2F22", "muted": "#8A7A6A", "hero": "warm", "radius": "12px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "boutique": {
        "bg": "#F8F6FB", "surface": "#FFFFFF", "accent": "#7A5C88", "accent2": "#B989A0",
        "ink": "#3C2E44", "muted": "#74677D", "hero": "light", "radius": "12px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "repair": {
        "bg": "#F4F7F5", "surface": "#FFFFFF", "accent": "#C05B2D", "accent2": "#5A7A6A",
        "ink": "#26323B", "muted": "#67757D", "hero": "strong", "radius": "10px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "education": {
        "bg": "#F4F8FD", "surface": "#FFFFFF", "accent": "#3B6BA5", "accent2": "#7C6BB0",
        "ink": "#243B4D", "muted": "#5F7290", "hero": "light", "radius": "12px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "fitness": {
        "bg": "#F6F8F7", "surface": "#FFFFFF", "accent": "#2E7D5B", "accent2": "#D97B2D",
        "ink": "#243A31", "muted": "#62796E", "hero": "strong", "radius": "10px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
    "generic": {
        "bg": "#F7F8FA", "surface": "#FFFFFF", "accent": "#3B5BDB", "accent2": "#6B7BDE",
        "ink": "#1F2430", "muted": "#626A78", "hero": "light", "radius": "12px",
        "font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    },
}

ICONS: dict[str, str] = {
    "phone": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M6.6 10.8c1.4 2.8 3.8 5.2 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.5.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1C10.6 21 3 13.4 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.2.2 2.4.6 3.5.1.3 0 .7-.2 1l-2.3 2.3z"/></svg>',
    "mail": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M3 5h18a1 1 0 0 1 1 1v12a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1zm9 7 9-4.2V8l-9 4.2L3 8v-.2L12 12z"/></svg>',
    "pin": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2a7 7 0 0 1 7 7c0 5.2-7 13-7 13S5 14.2 5 9a7 7 0 0 1 7-7zm0 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/></svg>',
    "clock": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm1-12h-2v6l5 3 1-1.5-4-2.5V8z"/></svg>',
    "whatsapp": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2a10 10 0 0 0-8.6 15L2 22l5.2-1.4A10 10 0 1 0 12 2zm5.1 13.6c-.2.6-1.2 1.1-1.7 1.2-.4.1-1 .1-1.6-.1-.4-.1-.9-.3-1.6-.6-2.9-1.3-4.8-4.2-5-4.4-.1-.2-1.2-1.6-1.2-3s.7-2.1 1-2.4c.2-.3.5-.4.7-.4h.5c.2 0 .3 0 .5.4.1.2.6 1.5.7 1.6.1.1.1.2 0 .4-.1.3-.2.4-.4.6l-.4.5c-.1.1-.2.3-.1.5.2.4.7 1.2 1.5 1.9 1 1 1.9 1.3 2.2 1.4.2.1.4.1.5-.1l.8-1c.2-.2.3-.2.5-.1 1.3.6 1.3.9 1.4 1z"/></svg>',
    "spark": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3zM19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z"/></svg>',
    "star": '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><path d="M12 2l2.9 6.3 6.9.8-5.1 4.7 1.4 6.8L12 17.4 5.9 20.6l1.4-6.8L2.2 9.1l6.9-.8L12 2z"/></svg>',
}


def theme_for_category(category: str | None) -> str:
    cat = (category or "").lower()
    for keywords, theme in CATEGORY_THEMES:
        if any(k in cat for k in keywords):
            return theme
    return "generic"


def all_themes() -> list[dict]:
    return [{"key": k, "name": k.capitalize()} for k in THEMES]


def render_demo_site(profile: dict[str, Any], business: dict[str, Any], sender: str = "", theme_override: str | None = None) -> str:
    """Render a complete demo page. profile may carry tagged claim lists (each
    item {'text','kind','source_fact_id'}) or plain string lists. business holds
    verified name/address/category/phone/email/whatsapp/opening_hours."""
    theme_key = theme_override or theme_for_category((business.get("category") or ""))
    t = THEMES.get(theme_key, THEMES["generic"])
    name = html.escape(business.get("name") or "Our business")
    category = html.escape(business.get("category") or "local business")
    summary = html.escape(profile.get("summary") or "")
    tone = html.escape(profile.get("tone") or "friendly and professional")

    services_raw = profile.get("services") or []
    services = _claim_texts(services_raw)
    services_verified = _any_verified(services_raw)
    selling_raw = profile.get("selling_points") or []
    selling = _claim_texts(selling_raw)

    opening_hours = profile.get("opening_hours") or business.get("opening_hours") or ""
    return _build_html(
        name=name, category=category, summary=summary, tone=tone,
        services=services, services_verified=services_verified,
        selling=selling, opening_hours=opening_hours,
        phone=business.get("phone") or "", email=business.get("email") or "",
        whatsapp=business.get("whatsapp") or business.get("phone") or "",
        address=business.get("address") or "",
        sender=(sender or ""), theme=t)

_is_placeholder_re = re.compile(r"example\.|@example|placeholder|your-email|example\.com")


def _build_html(*, name, category, summary, tone, services, services_verified,
                selling, opening_hours, phone, email, whatsapp, address, sender, theme) -> str:
    t = theme
    escaped = html.escape
    sender_to_show = (sender or "").strip()
    placeholder_sender = bool(_is_placeholder_re.search(sender_to_show))
    if not sender_to_show or placeholder_sender:
        identity = "Demo preview — sender identity not set yet"
        contact_email_ok = False
    else:
        identity = "Demo preview by " + escaped(sender_to_show)
        contact_email_ok = bool(email)

    phone_digits = re.sub(r"[^0-9+]", "", phone or "")
    wa_digits = re.sub(r"[^0-9]", "", whatsapp or "")
    maps_query = address.replace(" ", "+") if address else ""
    cta_primary = f'<a class="btn" href="tel:{phone_digits}">Call</a>' if phone_digits else ""
    cta_secondary = ""
    if services:
        cta_secondary = '<a class="btn ghost" href="#services">Our services</a>'
    elif address:
        cta_secondary = f'<a class="btn ghost" href="https://www.google.com/maps/search/?api=1&query={maps_query}" target="_blank" rel="nofollow noopener noreferrer">Find us</a>'

    header_ctas = ""
    if phone_digits:
        header_ctas = f'<a class="btn small-btn" href="tel:{phone_digits}">Call</a>'
        if wa_digits:
            header_ctas += f'<a class="btn ghost small-btn" href="https://wa.me/{wa_digits}" target="_blank" rel="noreferrer">WhatsApp</a>'

    contact_btns = ""
    if phone_digits:
        contact_btns += f'<a class="btn" href="tel:{phone_digits}">Call</a>\n'
    if wa_digits:
        contact_btns += f'<a class="btn ghost" href="https://wa.me/{wa_digits}" target="_blank" rel="noreferrer">WhatsApp</a>\n'
    if contact_email_ok:
        contact_btns += f'<a class="btn ghost" href="mailto:{escaped(email)}">Email</a>\n'
    if not contact_btns.strip():
        contact_btns = '<p class="muted small">Contact details to be confirmed with the owner.</p>'

    services_html = _services_markup(services, services_verified, category, escaped, t)
    why_html = _why_markup(selling, escaped, t)
    hours_html = ('<section class="block" aria-labelledby="h-hours"><h2 id="h-hours">Opening hours</h2>'
                  '<p class="muted">' + escaped(opening_hours) + '</p></section>') if opening_hours else ""
    address_html = ""
    if address:
        address_html = ('<section class="block" aria-labelledby="h-location"><h2 id="h-location">Location</h2>'
                        '<p class="row"><span class="icon">' + ICONS["pin"] + '</span> ' + escaped(address) + '</p>'
                        f'<p><a class="btn ghost" href="https://www.google.com/maps/search/?api=1&query={maps_query}" '
                        'target="_blank" rel="nofollow noopener noreferrer">Open in Google Maps</a></p></section>')

    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="robots" content="noindex,nofollow">\n'
        f'<title>{escaped(name)} — demo preview</title>\n'
        '<style>' + _css(t) + '</style>\n</head>\n<body>\n'
        '<a class="skip-link" href="#main">Skip to content</a>\n'
        '<div class="banner" role="note">' + identity + '</div>\n'
        '<header class="site-header"><div class="container header-inner">'
        '<span class="brand">' + escaped(name) + '</span>'
        '<div class="header-ctas">' + header_ctas + '</div></div></header>\n'
        '<main id="main" class="container">\n'
        '<section class="hero" aria-labelledby="h-hero">'
        f'<h1 id="h-hero">{escaped(name)}</h1>'
        f'<p class="tagline">{escaped(category)}</p>'
        f'<p class="lede">{escaped(summary or "")}</p>'
        '<div class="hero-ctas">' + cta_primary + cta_secondary + '</div></section>\n'
        '<section class="block" aria-labelledby="h-services"><h2 id="h-services">Services</h2>'
        '<ul class="cards">' + services_html + '</ul></section>\n'
        '<section class="block" aria-labelledby="h-about"><h2 id="h-about">About</h2>'
        '<p>' + escaped(summary or "Local, friendly service.") + '</p></section>\n'
        '<section class="block" aria-labelledby="h-why"><h2 id="h-why">Why choose us</h2>'
        '<ul class="cards">' + why_html + '</ul></section>\n'
        + hours_html + address_html +
        '<section class="block" aria-labelledby="h-contact"><h2 id="h-contact">Contact</h2>'
        + contact_btns + '</section>\n'
        '<footer><p class="muted small">' + identity + ' — '
        '<a href="#request-removal" data-removal="fake">Request removal</a></p></footer>\n'
        '</main>\n</body>\n</html>\n')


def _claim_texts(raw) -> list[str]:
    out = []
    for item in (raw or []):
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            txt = (item.get("text") or "").strip()
            if txt:
                out.append(txt)
    return out


def _any_verified(raw) -> bool:
    for item in (raw or []):
        if isinstance(item, dict) and item.get("kind") == "verified":
            return True
    return False


def _services_markup(services, services_verified, category, escaped, t) -> str:
    if not services:
        return ('<li class="card"><span class="icon">' + ICONS["spark"] + '</span>'
                '<div><strong>Sample services</strong>'
                '<p class="muted small">Typical services for a ' + escaped(category) +
                ' — to be confirmed with the owner.</p></div></li>')
    items = ""
    for s in services:
        items += ('<li class="card"><span class="icon">' + ICONS["spark"] + '</span>'
                  '<div><strong>' + escaped(s) + '</strong></div></li>\n')
    if not services_verified:
        items += ('<li class="card"><span class="icon">' + ICONS["spark"] + '</span>'
                  '<div><strong>Sample content</strong>'
                  '<p class="muted small">Service list is a sample — please confirm with the owner.</p></div></li>\n')
    return items


def _why_markup(selling, escaped, t) -> str:
    if not selling:
        return ('<li class="card"><span class="icon">' + ICONS["star"] + '</span>'
                '<div><p class="muted small">Why choose us — to be confirmed with the owner.</p></div></li>')
    items = ""
    for s in selling:
        items += ('<li class="card"><span class="icon">' + ICONS["star"] + '</span>'
                  '<div><p>' + escaped(s) + '</p></div></li>\n')
    return items


def _css(t: dict[str, Any]) -> str:
    return (
        "*{box-sizing:border-box}html,body{margin:0;padding:0;background:" + t["bg"] +
        ";color:" + t["ink"] + ";font-family:" + t["font"] +
        ";line-height:1.55;-webkit-text-size-adjust:100%}"
        "a{color:" + t["accent"] + "}"
        ".skip-link{position:absolute;left:-999px;top:0;background:" + t["accent"] +
        ";color:#fff;padding:8px 12px;z-index:50}"
        ".skip-link:focus{left:8px;top:8px}"
        ".banner{background:" + t["accent"] + ";color:#fff;text-align:center;padding:9px 14px;font-size:13px}"
        ".site-header{position:sticky;top:0;z-index:20;background:" + t["surface"] +
        ";border-bottom:1px solid rgba(0,0,0,.06);box-shadow:0 1px 6px rgba(0,0,0,.05)}"
        ".header-inner{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0}"
        ".brand{font-weight:700;font-size:17px}"
        ".header-ctas{display:flex;gap:8px;flex-wrap:wrap}"
        ".container{max-width:960px;margin:0 auto;padding:16px clamp(14px,4vw,28px) 40px}"
        ".hero{text-align:center;padding:56px 10px 36px;border-bottom:1px solid rgba(0,0,0,.05)}"
        ".hero h1{font-size:clamp(1.9rem,5vw,3rem);margin:0 0 6px;line-height:1.15;color:" + t["ink"] + "}"
        ".tagline{font-weight:600;color:" + t["accent2"] + ";margin:0 0 10px;text-transform:uppercase;letter-spacing:.04em;font-size:.9rem}"
        ".lede{max-width:640px;margin:0 auto 20px;color:" + t["muted"] + "}"
        ".hero-ctas{display:flex;gap:10px;justify-content:center;flex-wrap:wrap}"
        ".btn{display:inline-block;background:" + t["accent"] + ";color:#fff;padding:11px 20px;border-radius:" + t["radius"] +
        ";text-decoration:none;font-weight:600;border:1px solid transparent}"
        ".btn.ghost{background:transparent;color:" + t["accent"] + ";border-color:" + t["accent"] + "}"
        ".btn:focus-visible,a:focus-visible,button:focus-visible{outline:3px solid " + t["accent2"] + ";outline-offset:2px}"
        ".small-btn{font-size:.85rem;padding:7px 12px;margin:0}"
        ".block{margin-top:34px}"
        ".block h2{font-size:1.35rem;margin:0 0 12px;color:" + t["ink"] + "}"
        ".cards{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}"
        ".card{background:" + t["surface"] + ";border:1px solid rgba(0,0,0,.06);border-radius:" + t["radius"] +
        ";padding:14px;display:flex;gap:10px;align-items:flex-start}"
        ".card .icon{color:" + t["accent"] + ";flex:0 0 auto;margin-top:2px}"
        ".card strong{display:block;margin:0 0 2px}"
        ".row{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}"
        ".muted{color:" + t["muted"] + "}"
        ".small{font-size:.9rem}"
        "footer{border-top:1px solid rgba(0,0,0,.06);margin-top:48px;padding:26px 10px 34px;text-align:center}"
        "@media (max-width:600px){.header-ctas{gap:6px}.hero{padding-top:40px}}"
        "@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}"
    )
