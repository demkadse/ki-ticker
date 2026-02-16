#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
[cite_start]ADSENSE_PUB = "pub-2616688648278798" # [cite: 1]

DB_FILE = "news_db.json"
DAYS_TO_KEEP = 7
ITEMS_PER_CATEGORY = 20

HEADERS = {"User-Agent": "KI-TickerBot/1.0 (+https://ki-ticker.boehmonline.space)"}

# Kategorisierte Feeds: (Name, URL, Kategorie)
FEEDS = [
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "News & Trends"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/tag/artificial-intelligence/", "News & Trends"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "News & Trends"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI", "Forschung"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL", "Forschung"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/", "Unternehmen & Cloud"),
    ("OpenAI Blog", "https://openai.com/news/rss.xml", "Unternehmen & Cloud"),
]

AI_KEYWORDS = ["ki", "ai", "intelligence", "llm", "gpt", "model", "training", "robot", "nvidia", "openai", "claude", "gemini", "machine learning"]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_db(data):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_TO_KEEP)
    filtered = [i for i in data if datetime.datetime.fromisoformat(i["published_iso"]) > cutoff]
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered[:500], f, ensure_ascii=False, indent=2)

def is_ai_related(title, summary):
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in AI_KEYWORDS)

def extract_image(e):
    media = e.get("media_content") or []
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    content = e.get("summary", "") + e.get("description", "")
    if content:
        soup = BeautifulSoup(content, "html.parser")
        img = soup.find("img")
        if img and img.get("src"): return img["src"]
    return None

def fetch_feed(feed_info):
    name, url, category = feed_info
    print(f"[INFO] Lade {name}...")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            summary = e.get("summary") or e.get("description") or ""
            if not link or not is_ai_related(title, summary): continue

            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)

            out.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:12],
                "title": title,
                "url": link,
                "summary": BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:250] + "...",
                "source": name,
                "category": category,
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
    categories = ["News & Trends", "Forschung", "Unternehmen & Cloud"]
    html_content = ""

    for cat in categories:
        cat_items = [i for i in items if i["category"] == cat][:ITEMS_PER_CATEGORY]
        if not cat_items: continue
        
        html_content += f'<h2 class="category-title">{cat}</h2>'
        html_content += '<section class="grid">'
        for it in cat_items:
            dt = datetime.datetime.fromisoformat(it["published_iso"])
            img_html = f'<div class="img-container"><img src="{it["image"]}" loading="lazy" alt=""></div>' if it.get("image") else ""
            html_content += f"""
            <article class="card">
              {img_html}
              <div class="card-body">
                <div class="meta">{it["source"]} • {dt.strftime("%d.%m. %H:%M")}</div>
                <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
                <p>{it["summary"]}</p>
              </div>
            </article>"""
        html_content += '</section>'

    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <meta name="description" content="{SITE_DESC}">
    <link rel="stylesheet" href="style.css">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB}"></script>
</head>
<body>
    <header class="header">
        <h1>KI‑Ticker</h1>
        <p class="tagline">Update: {now.strftime("%d.%m.%Y %H:%M")} UTC</p>
    </header>
    <main class="container">
        {html_content}
    </main>
    <footer class="footer">&copy; {now.year} KI‑Ticker</footer>
</body>
</html>"""

def main():
    old_data = load_db()
    with ThreadPoolExecutor(max_workers=7) as executor:
        results = executor.map(fetch_feed, FEEDS)
    
    new_items = [item for sublist in results for item in sublist]
    combined = {item['url']: item for item in (old_data + new_items)}.values()
    sorted_items = sorted(combined, key=lambda x: x["published_iso"], reverse=True)
    
    save_db(list(sorted_items))
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(render_index(list(sorted_items)))
    print("[OK] Build abgeschlossen.")

if __name__ == "__main__":
    main()
