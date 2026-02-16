#!/usr/bin/env python3
import os
import time
import datetime
import hashlib
import json
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import requests
import feedparser
from bs4 import BeautifulSoup

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker – Aktuelle KI‑News"
SITE_DESC = "Automatisierte Übersicht zu KI, Machine Learning und LLMs."
SITE_URL = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"

DB_FILE = "news_db.json"
ITEMS_LIMIT = 80  # Etwas mehr Kapazität
DAYS_TO_KEEP = 7  # Wie lange News gespeichert bleiben

HEADERS = {"User-Agent": "KI-TickerBot/1.0 (+https://ki-ticker.boehmonline.space)"}

# KI-Keywords für den Filter
AI_KEYWORDS = ["ki", "ai", "intelligence", "llm", "gpt", "model", "training", "robot", "nvidia", "openai", "claude", "gemini", "machine learning"]

FEEDS = [
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/tag/artificial-intelligence/"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL"),
    ("OpenAI Blog", "https://openai.com/news/rss.xml"),
]

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_db(data):
    # Nur die letzten X Tage behalten
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_TO_KEEP)
    filtered = [i for i in data if datetime.datetime.fromisoformat(i["published_iso"]) > cutoff]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered[:300], f, ensure_ascii=False, indent=2)

def is_ai_related(title, summary):
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in AI_KEYWORDS)

def extract_image(e):
    # 1. Media Content (Standard)
    media = e.get("media_content") or []
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    
    # 2. Enclosures
    for l in e.get("links", []):
        if l.get("rel") == "enclosure" and "image" in l.get("type", ""):
            return l.get("href")
            
    # 3. BeautifulSoup im Content suchen (viele Blogs packen Bilder in die Description)
    content = e.get("summary", "") + e.get("description", "")
    if content:
        soup = BeautifulSoup(content, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            return img["src"]
    return None

def fetch_feed(feed_info):
    name, url = feed_info
    print(f"[INFO] Lade: {name}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = e.get("summary") or e.get("description") or ""
            
            if not link or not is_ai_related(title, summary):
                continue

            pub_date = (e.get("published_parsed") or e.get("updated_parsed"))
            dt = datetime.datetime.fromtimestamp(time.mktime(pub_date), datetime.timezone.utc) if pub_date else datetime.datetime.now(datetime.timezone.utc)

            out.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:12],
                "title": title,
                "url": link,
                "summary": BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:250] + "...",
                "source": name,
                "published_iso": dt.isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": extract_image(e)
            })
        return out
    except Exception as ex:
        print(f"[ERROR] {name}: {ex}")
        return []

def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    cards = ""
    for it in items:
        dt = datetime.datetime.fromisoformat(it["published_iso"])
        img_html = f'<div class="img-container"><img src="{it["image"]}" loading="lazy"></div>' if it.get("image") else ""
        cards += f"""
        <article class="card">
          {img_html}
          <div class="content">
            <div class="meta">{it["source"]} • {dt.strftime("%d.%m. %H:%M")}</div>
            <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
            <p>{it["summary"]}</p>
          </div>
        </article>"""

    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB}"></script>
</head>
<body>
    <header class="header"><h1>KI‑Ticker</h1><p>Update: {now.strftime("%H:%M")} UTC</p></header>
    <main class="grid">{cards}</main>
    <footer class="footer">&copy; {now.year} KI‑Ticker</footer>
</body>
</html>"""

def main():
    old_data = load_db()
    
    # Parallelisierung
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = executor.map(fetch_feed, FEEDS)
    
    new_items = [item for sublist in results for item in sublist]
    
    # Zusammenführen & Deduplizieren
    combined = {item['url']: item for item in (old_data + new_items)}.values()
    sorted_items = sorted(combined, key=lambda x: x["published_iso"], reverse=True)
    
    save_db(list(sorted_items))
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render_index(list(sorted_items)[:ITEMS_LIMIT]))

if __name__ == "__main__":
    main()
