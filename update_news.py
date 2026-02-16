#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import datetime
import hashlib
import json
import math
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

import requests
import feedparser
from bs4 import BeautifulSoup

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker – Aktuelle KI‑News"
SITE_DESC = "Automatisierte Übersicht zu KI, Machine Learning und LLMs."
[cite_start]ADSENSE_PUB = "pub-2616688648278798" [cite: 1]

DB_FILE = "news_db.json"
DAYS_TO_KEEP = 7
ITEMS_PER_CATEGORY = 20

HEADERS = {"User-Agent": "KI-TickerBot/1.0 (+https://ki-ticker.boehmonline.space)"}

FEEDS = [
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", "News & Trends"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/tag/artificial-intelligence/", "News & Trends"),
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/", "News & Trends"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI", "Forschung"),
    ("arXiv cs.CL", "https://export.arxiv.org/rss/cs.CL", "Forschung"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/", "Unternehmen & Cloud"),
    ("OpenAI Blog", "https://openai.com/news/rss.xml", "Unternehmen & Cloud"),
]

# Keyword-Mapping für automatische Tags
TAG_MAPPING = {
    "nvidia": "Hardware", "gpu": "Hardware", "h100": "Hardware", "blackwell": "Hardware",
    "arxiv": "Research", "paper": "Research", "study": "Research",
    "openai": "LLM", "gpt": "LLM", "claude": "LLM", "gemini": "LLM", "anthropic": "LLM",
    "robot": "Robotics", "roboter": "Robotics", "agent": "Agents",
    "apple": "Big Tech", "google": "Big Tech", "meta": "Big Tech", "microsoft": "Big Tech"
}

AI_KEYWORDS = ["ki", "ai", "intelligence", "llm", "gpt", "model", "training", "robot", "nvidia", "openai", "claude", "gemini", "machine learning"]

def get_reading_time(text):
    words = text.split()
    return max(1, math.ceil(len(words) / 200))

def get_tags(title, summary):
    tags = []
    text = f"{title} {summary}".lower()
    for kw, tag in TAG_MAPPING.items():
        if kw in text and tag not in tags:
            tags.append(tag)
    return tags

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
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            raw_summary = e.get("summary") or e.get("description") or ""
            clean_summary = BeautifulSoup(raw_summary, "html.parser").get_text(" ", strip=True)
            
            if not link or not is_ai_related(title, clean_summary): continue

            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)

            out.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:12],
                "title": title,
                "url": link,
                "summary": clean_summary[:250] + "...",
                "source": name,
                "category": category,
                "published_iso": dt.isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": extract_image(e),
                "reading_time": get_reading_time(clean_summary),
                "tags": get_tags(title, clean_summary)
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
            
            # Tags generieren
            badges = "".join([f'<span class="badge">{t}</span>' for t in it.get("tags", [])])
            
            html_content += f"""
            <article class="card" data-content="{it["title"].lower()} {it["summary"].lower()}">
              {img_html}
              <div class="card-body">
                <div class="badge-container">{badges}</div>
                <div class="meta">{it["source"]} • {dt.strftime("%d.%m. %H:%M")} • {it["reading_time"]} Min. Lesezeit</div>
                <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
                <p>{it["summary"]}</p>
              </div>
            </article>"""
        html_content += '</section>'

    # ... (Rest der HTML-Struktur inkl. Script bleibt gleich wie in Schritt 3)
    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_PUB}"></script>
</head>
<body class="dark-mode">
    <header class="header">
        <h1>KI‑Ticker</h1>
        <div class="controls">
            <input type="text" id="searchInput" placeholder="News durchsuchen...">
            <button class="btn-toggle" id="themeToggle">🌓</button>
        </div>
        <p class="tagline">Letztes Update: {now.strftime("%d.%m.%Y %H:%M")} UTC</p>
    </header>
    <main class="container" id="newsContainer">
        {html_content}
    </main>
    <footer class="footer">&copy; {now.year} KI‑Ticker</footer>

    <script>
        const themeToggle = document.getElementById('themeToggle');
        const body = document.body;
        if (localStorage.getItem('theme') === 'light') body.classList.remove('dark-mode');

        themeToggle.addEventListener('click', () => {{
            body.classList.toggle('dark-mode');
            localStorage.setItem('theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
        }});

        const searchInput = document.getElementById('searchInput');
        searchInput.addEventListener('input', (e) => {{
            const term = e.target.value.toLowerCase();
            document.querySelectorAll('.card').forEach(card => {{
                card.style.display = card.getAttribute('data-content').includes(term) ? '' : 'none';
            }});
            document.querySelectorAll('.category-title').forEach(title => {{
                const section = title.nextElementSibling;
                const hasVisible = Array.from(section.querySelectorAll('.card')).some(c => c.style.display !== 'none');
                title.style.display = hasVisible ? '' : 'none';
            }});
        }});
    </script>
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

if __name__ == "__main__":
    main()
