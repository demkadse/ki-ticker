#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Minimaler KI‑Ticker: 
- RSS holen 
- Artikel normalisieren 
- HTML generieren 
- index.html überschreiben
- ads.txt aktualisieren
"""

import os
import time
import datetime
import hashlib
from urllib.parse import urlparse

import requests
import feedparser
from bs4 import BeautifulSoup

# ------------------------------------------------------------
# Einstellungen
# ------------------------------------------------------------
SITE_TITLE = "KI‑Ticker – Aktuelle KI‑News"
SITE_DESC  = "Automatisierte Übersicht zu KI, Machine Learning, LLMs und Forschung."
SITE_URL   = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"

ITEMS_LIMIT = 60  # Anzahl Artikel auf der Startseite

# HTTP Header für Feeds
HEADERS = {
    "User-Agent": "KI-TickerBot/1.0 (+https://ki-ticker.boehmonline.space)"
}

# RSS‑Feeds (nur stabile Quellen)
FEEDS = [
    ("The Verge – AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Technology Review – AI", "https://www.technologyreview.com/feed/tag/artificial-intelligence/"),
    ("VentureBeat – AI", "https://venturebeat.com/category/ai/feed/"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL"),
]

# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------
def clean_html(text, max_len=280):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    txt = soup.get_text(" ", strip=True)
    if len(txt) > max_len:
        txt = txt[:max_len].rstrip() + "…"
    return txt


def make_id(*parts):
    h = hashlib.sha256()
    for p in parts:
        if p:
            h.update(str(p).encode("utf-8", errors="ignore"))
    return h.hexdigest()[:16]


def extract_published(entry):
    ts = entry.get("published_parsed") or entry.get("updated_parsed")
    if ts:
        return datetime.datetime.fromtimestamp(time.mktime(ts), tz=datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)


def extract_image(entry):
    media = entry.get("media_content") or []
    if isinstance(media, list) and media:
        url = media[0].get("url")
        if url:
            return url

    for l in entry.get("links", []):
        if l.get("rel") == "enclosure" and "image" in l.get("type", ""):
            return l.get("href")

    return None


# ------------------------------------------------------------
# Feeds laden
# ------------------------------------------------------------
def fetch_feed(name, url):
    print(f"[INFO] Lade Feed: {name}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)

        items = []
        for e in fp.entries[:40]:
            title = (e.get("title") or "").strip()
            link  = (e.get("link") or "").strip()
            if not link:
                continue

            summary = clean_html(e.get("summary") or e.get("description") or "")
            pub_dt  = extract_published(e)
            img     = extract_image(e)

            items.append({
                "id": make_id(name, title, link),
                "title": title or "(ohne Titel)",
                "url": link,
                "summary": summary,
                "source": name,
                "published": pub_dt,
                "published_iso": pub_dt.isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": img
            })

        return items

    except Exception as ex:
        print(f"[ERROR] Fehler beim Abrufen {name}: {ex}")
        return []


def fetch_all():
    out = []
    for name, url in FEEDS:
        out.extend(fetch_feed(name, url))
    return out


# ------------------------------------------------------------
# Deduplikation
# ------------------------------------------------------------
def dedupe_and_sort(items):
    seen = set()
    out = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        key = (it["title"].lower().strip(), it["domain"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) >= ITEMS_LIMIT:
            break
    return out


# ------------------------------------------------------------
# HTML Renderer
# ------------------------------------------------------------
def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    last_updated = now.strftime("%d.%m.%Y %H:%M UTC")

    def card(it):
        img_html = ""
        if it["image"]:
            img_html = f'{it[<img src="{       return f"""
        <article class="card">
          {img_html}
          <h3><a href="{it["url"/a></h3>
          <div class="meta">{it["source"]} • {it["domain"]} • {it["published"].strftime("%d.%m.%Y %H:%M")} UTC</div>
          {f'<p>{it["summary"]}</p>' if it["summary"] else ""}
        </article>
        """

    cards_html = "\n".join(card(i) for i in items)

    html = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE}</title>
<meta name="description" content="{SITE_DESC}">
{SITE_URL}
<link rel="stylesheet" href="ttps://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB}</script>
</head>

<body>
<header class="header">
  <a class="brand"h1></a>
  <p class="tagline">Automatisch aktualisierte Nachrichten. Zuletzt aktualisiert: {last_updated}</p>
</header>

<main>
  <section class="grid">
    {cards_html}
  </section>
</main>

<footer class="footer">
  <p>&copy; {now.year} KI‑Ticker</p>
</footer>
</body>
</html>
"""
    return html


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
def main():
    print("============================================================")
    print("  KI‑Ticker (minimal) gestartet")
    print("============================================================")

    items = fetch_all()
    print(f"[INFO] Roh-Artikel: {len(items)}")

    items = dedupe_and_sort(items)
    print(f"[INFO] Nach Deduplikation: {len(items)}")

    html = render_index(items)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    with open("ads.txt", "w", encoding="utf-8") as f:
        f.write(f"google.com, {ADSENSE_PUB}, DIRECT, f08c47fec0942fa0\n")

    print("[OK] index.html aktualisiert")
    print("[OK] ads.txt aktualisiert")
    print("============================================================")
    print("Build fertig.")
    print("============================================================")


if __name__ == "__main__":
    main()
