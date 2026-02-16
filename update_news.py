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
SITE_URL = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"
ADSENSE_SLOT = "8395864605"

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
TAG_MAPPING = {"nvidia": "Hardware", "gpu": "Hardware", "openai": "LLM", "gpt": "LLM", "claude": "LLM", "gemini": "LLM", "robot": "Robotics", "agent": "Agents"}

def get_reading_time(text):
    words = text.split()
    return max(1, math.ceil(len(words) / 200))

def get_tags(title, summary):
    tags = []
    text = f"{title} {summary}".lower()
    for kw, tag in TAG_MAPPING.items():
        if kw in text and tag not in tags: tags.append(tag)
    return tags

def get_top_keywords(items, limit=8):
    words = []
    for it in items:
        found = re.findall(r'\w+', it['title'].lower())
        words.extend([w for w in found if len(w) > 3 and w not in STOP_WORDS])
    return [word for word, count in Counter(words).most_common(limit)]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_db(data):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_TO_KEEP)
    filtered = [i for i in data if datetime.datetime.fromisoformat(i["published_iso"]) > cutoff]
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(filtered[:500], f, ensure_ascii=False, indent=2)

def is_ai_related(title, summary):
    text = f"{title} {summary}".lower()
    kw = ["ki", "ai", "intelligence", "llm", "gpt", "model", "training", "robot", "nvidia", "openai", "claude", "gemini"]
    return any(k in text for k in kw)

def get_fallback_image(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            og = soup.find("meta", property="og:image")
            return og["content"] if og else None
    except: pass
    return None

def extract_image(e, link):
    media = e.get("media_content") or []
    if media and isinstance(media, list) and media[0].get("url"): return media[0]["url"]
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
                "title": title, "url": link, "summary": clean_summary[:250] + "...",
                "source": name, "category": category, "published_iso": dt.isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": extract_image(e, link), "reading_time": get_reading_time(clean_summary),
                "tags": get_tags(title, clean_summary)
            })
        return out
    except: return []

def generate_sitemap(items):
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    sitemap += f'  <url><loc>{SITE_URL}/</loc><priority>1.0</priority></url>\n'
    for it in items[:100]: sitemap += f'  <url><loc>{it["url"]}</loc></url>\n'
    sitemap += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap)

def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    top_story = items[0]
    display_items = items[1:]
    trends_html = "".join([f'<button class="trend-tag" onclick="setSearch(\'{kw}\')">#{kw}</button>' for kw in get_top_keywords(items)])
    
    ad_block = f'<div class="ad-container"><ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'
    
    # NEU: SIDEBAR ADS
    sidebar_ad = f'<div class="sidebar-ad"><ins class="adsbygoogle" style="display:block" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT}" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'

    hero_img = f'style="background-image: url(\'{top_story["image"]}\')"' if top_story.get("image") else ""
    hero_html = f'<section class="hero" data-id="{top_story["id"]}" data-content="{top_story["title"].lower()}"><div class="hero-image" {hero_img}></div><div class="hero-content"><span class="badge" style="background:var(--acc); color:white;">🔥 Top Story</span><div class="meta">{top_story["source"]} • {datetime.datetime.fromisoformat(top_story["published_iso"]).strftime("%d.%m. %H:%M")}</div><h1><a href="{top_story["url"]}" target="_blank">{top_story["title"]}</a></h1><p>{top_story["summary"]}</p><div class="share-bar"><button onclick="toggleBookmark(\'{top_story["id"]}\')" class="btn-bookmark">🔖</button></div></div></section>'

    categories = ["News & Trends", "Forschung", "Unternehmen & Cloud"]
    html_content = ""
    for cat in categories:
        cat_items = [i for i in display_items if i["category"] == cat][:ITEMS_PER_CATEGORY]
        if not cat_items: continue
        html_content += f'<div class="cat-section" data-category="{cat}"><h2 class="category-title">{cat}</h2><section class="grid">'
        for idx, it in enumerate(cat_items):
            dt = datetime.datetime.fromisoformat(it["published_iso"])
            img_html = f'<div class="img-container"><img src="{it["image"]}" loading="lazy"></div>' if it.get("image") else ""
            badges = "".join([f'<span class="badge">{t}</span>' for t in it.get("tags", [])])
            html_content += f'<article class="card" data-id="{it["id"]}" data-content="{it["title"].lower()} {it["summary"].lower()}">{img_html}<div class="card-body"><div class="badge-container">{badges}</div><div class="meta"><img src="https://www.google.com/s2/favicons?domain={it["domain"]}&sz=32" class="source-icon"> {it["source"]} • {dt.strftime("%d.%m. %H:%M")}</div><h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3><p>{it["summary"]}</p><div class="share-bar"><button onclick="toggleBookmark(\'{it["id"]}\')" class="btn-bookmark">🔖</button><button onclick="copyToClipboard(\'{it["url"]}\')">🔗</button></div></div></article>'
            if (idx + 1) % 6 == 0: html_content += ad_block
        html_content += '</section></div>'

    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <meta name="description" content="{SITE_DESC}">
    <link rel="stylesheet" href="style.css">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{ADSENSE_PUB}" crossorigin="anonymous"></script>
</head>
<body class="dark-mode">
    <header class="header">
        <h1>KI‑Ticker</h1>
        <div class="controls"><input type="text" id="searchInput" placeholder="News durchsuchen..."><button class="btn-toggle" id="themeToggle">🌓</button></div>
        <div class="trends">{trends_html}</div>
    </header>
    
    <div class="main-wrapper">
        {sidebar_ad}
        <main class="container">{hero_html}{html_content}</main>
        {sidebar_ad}
    </div>

    <button id="backToTop">↑</button>
    <footer class="footer">
        <p>&copy; {now.year} KI‑Ticker</p>
        <div class="footer-links">
            <a href="impressum.html">Impressum</a>
            <a href="datenschutz.html">Datenschutz</a>
        </div>
    </footer>
    <script>
        const body = document.body;
        if (localStorage.getItem('theme') === 'light') body.classList.remove('dark-mode');
        document.getElementById('themeToggle').onclick = () => {{
            body.classList.toggle('dark-mode');
            localStorage.setItem('theme', body.classList.contains('dark-mode') ? 'dark' : 'light');
        }};
        function filterNews(term) {{
            const t = term.toLowerCase();
            document.querySelectorAll('.card, .hero').forEach(el => {{
                el.style.display = (el.getAttribute('data-content') || "").includes(t) ? '' : 'none';
            }});
        }}
        function toggleBookmark(id) {{
            let b = JSON.parse(localStorage.getItem('bookmarks') || '[]');
            if(b.includes(id)) b = b.filter(i => i!==id); else b.push(id);
            localStorage.setItem('bookmarks', JSON.stringify(b));
            updateBookmarkUI();
        }}
        function updateBookmarkUI() {{
            const b = JSON.parse(localStorage.getItem('bookmarks') || '[]');
            document.querySelectorAll('.btn-bookmark').forEach(btn => {{
                const parent = btn.closest('[data-id]');
                if(parent) btn.style.color = b.includes(parent.dataset.id) ? 'var(--acc)' : '';
            }});
        }}
        document.getElementById('searchInput').oninput = (e) => filterNews(e.target.value);
        function setSearch(t) {{ document.getElementById('searchInput').value=t; filterNews(t); }}
        window.onscroll = () => document.getElementById("backToTop").style.display = window.scrollY > 500 ? "block" : "none";
        document.getElementById("backToTop").onclick = () => window.scrollTo({{top:0, behavior:'smooth'}});
        function copyToClipboard(t) {{ navigator.clipboard.writeText(t).then(() => alert('Link kopiert!')); }}
        updateBookmarkUI();
    </script>
</body>
</html>"""

def main():
    db = load_db()
    with ThreadPoolExecutor(max_workers=7) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = [i for r in res for i in r]
    all_data = sorted({i['url']: i for i in (db + items)}.values(), key=lambda x: x["published_iso"], reverse=True)
    save_db(all_data)
    generate_sitemap(all_data)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(all_data))

if __name__ == "__main__": main()
