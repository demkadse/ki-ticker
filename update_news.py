#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import datetime
import hashlib
import json
import math
import urllib.parse
from urllib.parse import urlparse
from collections import Counter
import re
from concurrent.futures import ThreadPoolExecutor

import requests
import feedparser
from bs4 import BeautifulSoup

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker – Aktuelle KI‑News"
SITE_DESC = "Automatisierte Übersicht zu KI, Machine Learning und LLMs."
ADSENSE_PUB = "pub-2616688648278798"

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

STOP_WORDS = {"and", "the", "for", "with", "how", "from", "what", "this", "der", "die", "das", "und", "für", "mit", "von", "den", "auf", "ist", "ki-ticker", "new", "news", "ai", "ki"}
TAG_MAPPING = {
    "nvidia": "Hardware", "gpu": "Hardware", "openai": "LLM", "gpt": "LLM", 
    "claude": "LLM", "gemini": "LLM", "robot": "Robotics", "agent": "Agents",
    "apple": "Big Tech", "google": "Big Tech", "meta": "Big Tech", "microsoft": "Big Tech"
}

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

def get_top_keywords(items, limit=8):
    words = []
    for it in items:
        found = re.findall(r'\w+', it['title'].lower())
        words.extend([w for w in found if len(w) > 3 and w not in STOP_WORDS])
    most_common = Counter(words).most_common(limit)
    return [word for word, count in most_common]

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
    AI_KEYWORDS = ["ki", "ai", "intelligence", "llm", "gpt", "model", "training", "robot", "nvidia", "openai", "claude", "gemini", "machine learning"]
    return any(kw in text for kw in AI_KEYWORDS)

def get_fallback_image(url):
    """Versucht ein Vorschaubild direkt von der Webseite zu scrapen."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            # Suche nach OpenGraph Image
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                return og_img["content"]
            # Suche nach Twitter Image
            tw_img = soup.find("meta", name="twitter:image")
            if tw_img and tw_img.get("content"):
                return tw_img["content"]
    except:
        pass
    return None

def extract_image(e, link):
    # 1. Media Content aus Feed
    media = e.get("media_content") or []
    if media and isinstance(media, list) and media[0].get("url"):
        return media[0]["url"]
    
    # 2. BeautifulSoup im Content des Feeds suchen
    content = e.get("summary", "") + e.get("description", "")
    if content:
        soup = BeautifulSoup(content, "html.parser")
        img = soup.find("img")
        if img and img.get("src"): 
            return img["src"]
            
    # 3. Fallback: Webseite direkt scrapen
    return get_fallback_image(link)

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
                "image": extract_image(e, link),
                "reading_time": get_reading_time(clean_summary),
                "tags": get_tags(title, clean_summary)
            })
        return out
    except Exception as ex:
        print(f"[ERROR] {name}: {ex}")
        return []

def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    if not items: return "Keine News gefunden."
    
    top_story = items[0]
    display_items = items[1:]
    top_keywords = get_top_keywords(items)
    trends_html = "".join([f'<button class="trend-tag" onclick="setSearch(\'{kw}\')">#{kw}</button>' for kw in top_keywords])
    
    dt_hero = datetime.datetime.fromisoformat(top_story["published_iso"])
    hero_img = f'style="background-image: url(\'{top_story["image"]}\')"' if top_story.get("image") else ""
    hero_html = f"""
    <section class="hero" data-content="{top_story["title"].lower()}">
        <div class="hero-image" {hero_img}></div>
        <div class="hero-content">
            <span class="badge" style="background:var(--acc); color:white;">Top Story</span>
            <div class="meta">{top_story["source"]} • {dt_hero.strftime("%d.%m. %H:%M")}</div>
            <h1><a href="{top_story["url"]}" target="_blank">{top_story["title"]}</a></h1>
            <p>{top_story["summary"]}</p>
        </div>
    </section>
    """

    categories = ["News & Trends", "Forschung", "Unternehmen & Cloud"]
    html_content = ""

    for cat in categories:
        cat_items = [i for i in display_items if i["category"] == cat][:ITEMS_PER_CATEGORY]
        if not cat_items: continue
        
        html_content += f'<h2 class="category-title">{cat}</h2>'
        html_content += '<section class="grid">'
        for it in cat_items:
            dt = datetime.datetime.fromisoformat(it["published_iso"])
            img_html = f'<div class="img-container"><img src="{it["image"]}" loading="lazy" alt=""></div>' if it.get("image") else ""
            badges = "".join([f'<span class="badge">{t}</span>' for t in it.get("tags", [])])
            
            encoded_title = urllib.parse.quote(it["title"])
            encoded_url = urllib.parse.quote(it["url"])
            share_x = f"https://twitter.com/intent/tweet?text={encoded_title}&url={encoded_url}"
            share_li = f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
            
            html_content += f"""
            <article class="card" data-content="{it["title"].lower()} {it["summary"].lower()}">
              {img_html}
              <div class="card-body">
                <div class="badge-container">{badges}</div>
                <div class="meta">{it["source"]} • {dt.strftime("%d.%m. %H:%M")} • {it["reading_time"]} Min.</div>
                <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
                <p>{it["summary"]}</p>
                <div class="share-bar">
                    <a href="{share_x}" target="_blank" title="Auf X teilen">𝕏</a>
                    <a href="{share_li}" target="_blank" title="Auf LinkedIn teilen">in</a>
                    <button onclick="copyToClipboard('{it["url"]}')" title="Link kopieren">🔗</button>
                </div>
              </div>
            </article>"""
        html_content += '</section>'

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
        <div class="trends">
            <span style="font-size:12px; color:var(--muted); margin-right:10px;">Trends:</span>
            {trends_html}
        </div>
        <p class="tagline">Update: {now.strftime("%d.%m.%Y %H:%M")} UTC</p>
    </header>
    <main class="container">
        {hero_html}
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
        function filterNews(term) {{
            const search = term.toLowerCase();
            document.querySelectorAll('.card, .hero').forEach(el => {{
                const content = el.getAttribute('data-content') || "";
                el.style.display = content.includes(search) ? '' : 'none';
            }});
            document.querySelectorAll('.category-title').forEach(title => {{
                const section = title.nextElementSibling;
                const hasVisible = section && Array.from(section.querySelectorAll('.card')).some(c => c.style.display !== 'none');
                title.style.display = hasVisible ? '' : 'none';
            }});
        }}

        searchInput.addEventListener('input', (e) => filterNews(e.target.value));

        function setSearch(term) {{
            searchInput.value = term;
            filterNews(term);
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                alert('Link kopiert!');
            }});
        }}
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
    print("[OK] Build abgeschlossen.")

if __name__ == "__main__":
    main()
