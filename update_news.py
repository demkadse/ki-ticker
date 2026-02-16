
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import datetime
import hashlib
from urllib.parse import urlparse

import requests
import feedparser
from bs4 import BeautifulSoup

SITE_TITLE = "KI‑Ticker – Aktuelle KI‑News"
SITE_DESC  = "Automatisierte Übersicht zu KI, Machine Learning, LLMs und Forschung."
SITE_URL   = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"

ITEMS_LIMIT = 60

HEADERS = {
    "User-Agent": "KI-TickerBot/1.0 (+https://ki-ticker.boehmonline.space)"
}

FEEDS = [
    ("The Verge – AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Technology Review – AI", "https://www.technologyreview.com/feed/tag/artificial-intelligence/"),
    ("VentureBeat – AI", "https://venturebeat.com/category/ai/feed/"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL"),
]

def clean_html(text, max_len=280):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    s = soup.get_text(" ", strip=True)
    return (s[:max_len] + "…") if len(s) > max_len else s

def make_id(*parts):
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8", errors="ignore"))
    return h.hexdigest()[:16]

def extract_published(e):
    ts = e.get("published_parsed") or e.get("updated_parsed")
    if ts:
        return datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc)
    return datetime.datetime.now(datetime.timezone.utc)

def extract_image(e):
    media = e.get("media_content") or []
    if isinstance(media, list) and media:
        if media[0].get("url"):
            return media[0]["url"]
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and "image" in l.get("type", ""):
            return l.get("href")
    return None

def fetch_feed(name, url):
    print(f"[INFO] Lade Feed: {name}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries[:40]:
            title = (e.get("title") or "").strip()
            link  = (e.get("link") or "").strip()
            if not link:
                continue
            out.append({
                "id": make_id(name, title, link),
                "title": title or "(ohne Titel)",
                "url": link,
                "summary": clean_html(e.get("summary") or e.get("description") or ""),
                "source": name,
                "published": extract_published(e),
                "published_iso": extract_published(e).isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": extract_image(e)
            })
        return out
    except Exception as ex:
        print(f"[ERROR] {name}: {ex}")
        return []

def fetch_all():
    out = []
    for name, url in FEEDS:
        out.extend(fetch_feed(name, url))
    return out

def dedupe_and_sort(items):
    seen = set()
    out = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        key = (it["title"].lower(), it["domain"])
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
        if len(out) >= ITEMS_LIMIT:
            break
    return out

def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    last = now.strftime("%d.%m.%Y %H:%M UTC")

    def card(it):
        img = f'<a href="{it["url"]}" target="_blank
        summary = f'<p>{it["summary"]}</p>' if it["summary"] else ""
        return f"""
        <article class="card">
          {img}
          <h3>{it[{it["title"]}</a></h3>
          <div class="meta">{it["source"]} • {it["domain"]} • {it["published"].strftime("%d.%m.%Y %H:%M")} UTC</div>
          {summary}
        </article>
        """

    cards = "\n".join(card(i) for i in items)

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{SITE_TITLE}</title>
<meta name="description" content="{SITE_DESC}">
{SITE_URL}
<link.css

https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB}</script>
</head>
<body>
<header class="header">
  <h1>KI‑Ticker</h1>
  <p class="tagline">Zuletzt aktualisiert: {last}</p>
</header>
<main>
<section class="grid">
{cards}
</section>
</main>
<footer class="footer">
  <p>&copy; {now.year} KI‑Ticker</p>
</footer>
</body>
</html>
"""

def main():
    print("== KI‑Ticker Build ==")
    items = fetch_all()
    items = dedupe_and_sort(items)
    html = render_index(items)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    with open("ads.txt", "w", encoding="utf-8") as f:
        f.write(f"google.com, {ADSENSE_PUB}, DIRECT, f08c47fec0942fa0\n")

    print("[OK] Fertig.")

if __name__ == "__main__":
    main()
