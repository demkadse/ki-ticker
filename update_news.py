#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, hashlib, json, re, html
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import requests, feedparser

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"
ADSENSE_SLOT_LEFT = "3499497230"
ADSENSE_SLOT_RIGHT = "8513926860"
ADSENSE_SLOT_FEED = "8395864605"
HERO_BASE = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80"
DB_FILE = "news_db.json"
EDITORIAL_FILE = "editorial.json"

FEEDS = [
    ("NVIDIA Blog", "https://blogs.nvidia.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Futurism", "https://futurism.com/feed"),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("arXiv", "https://export.arxiv.org/rss/cs.AI"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def load_editorial():
    if os.path.exists(EDITORIAL_FILE):
        try:
            with open(EDITORIAL_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

def get_youtube_id(url):
    if not url: return None
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be': return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch': return parse_qs(parsed.query).get('v', [None])[0]
        if parsed.path.startswith(('/embed/', '/v/')): return parsed.path.split('/')[2]
    return None

def fetch_feed(feed_info):
    name, url = feed_info
    try:
        resp = requests.get(url, timeout=15)
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries:
            link = (e.get("link") or "").strip()
            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)
            out.append({
                "title": e.get("title", "").strip(), "url": link, "source": name, 
                "published_iso": dt.isoformat(), "domain": urlparse(link).netloc.replace("www.", ""),
                "image": "" # Vereinfacht für dieses Layout
            })
        return out
    except: return []

def render_index(items, editorial):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    hero_default = f"{HERO_BASE}&w=800"
    
    # Gruppierung nach Quelle
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    # Sortierung der Quellen: Die mit der neuesten News nach oben
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["published_iso"], reverse=True)

    editorial_html = ""
    if editorial:
        yt_id = get_youtube_id(editorial.get('video_url'))
        video_embed = f'<div class="video-container"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        editorial_html = f"""
        <section class="editorial-section">
            <div class="editorial-badge"><i class="fa-solid fa-star"></i> Tagesthema</div>
            <div class="editorial-card">
                <h2>{editorial.get('title', '...')}</h2>
                {video_embed}
                <div class="editorial-text">{editorial.get('content', '')}</div>
                <div class="editorial-footer">
                    <button class="filter-action-btn" onclick="applySearch('{editorial.get('search_term','')}');">
                        <i class="fa-solid fa-magnifying-glass"></i> Passende News finden
                    </button>
                    <div class="editorial-date">Stand: {editorial.get('date', '')}</div>
                </div>
            </div>
        </section>"""

    main_content = ""
    for src in sorted_sources:
        cards_html = ""
        source_url = f"https://{grouped[src][0]['domain']}"
        
        for it in grouped[src]:
            dt = datetime.datetime.fromisoformat(it["published_iso"])
            cards_html += f"""
            <article class="card" data-content="{it["title"].lower()}">
              <div class="img-container"><img src="{hero_default}" alt="" loading="lazy"></div>
              <div class="card-body">
                <div class="meta">{dt.strftime("%d.%m. • %H:%M")}</div>
                <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
                <div class="share-bar"><button onclick="copyToClipboard('{it['url']}')"><i class="fa-solid fa-link"></i> Link</button></div>
              </div>
            </article>"""
        
        # Der Deep-Dive Button am Ende jeder Zeile
        cards_html += f"""
        <article class="card deep-dive-card">
            <div class="card-body" style="justify-content:center; align-items:center;">
                <p style="margin-bottom:15px; font-weight:600;">Lust auf den Deep-Dive?</p>
                <a href="{source_url}" target="_blank" class="deep-dive-btn">
                    Alle weiteren Artikel direkt bei {src} <i class="fa-solid fa-arrow-up-right-from-square"></i>
                </a>
            </div>
        </article>"""

        main_content += f"""
        <section class="source-section">
            <div class="source-title">
                <img src="https://www.google.com/s2/favicons?domain={grouped[src][0]['domain']}&sz=32" alt="">
                {src}
            </div>
            <div class="carousel-wrapper">
                <div class="news-carousel">{cards_html}</div>
            </div>
        </section>"""

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <link rel="stylesheet" href="style.css?v={int(time.time())}"></head>
    <body class="dark-mode"><div class="site-layout">
        <aside class="sidebar-ad left"></aside>
        <main class="container">
            <header class="header"><h1>KI‑Ticker</h1><div class="search-wrapper"><input type="text" id="searchInput" placeholder="Feed durchsuchen..."></div></header>
            {editorial_html}
            {main_content}
            <footer class="footer"><p>&copy; 2026 KI‑Ticker | <a href="ueber-uns.html">Über uns</a> | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p></footer>
        </main>
        <aside class="sidebar-ad right"></aside>
    </div>
    <script>
        function filterNews(t){{
            const v = t.toLowerCase();
            document.querySelectorAll('.card').forEach(el => {{
                if(!el.classList.contains('deep-dive-card')) {{
                    const match = el.getAttribute('data-content').includes(v);
                    el.style.display = match ? 'flex' : 'none';
                }}
            }});
        }}
        function applySearch(word) {{ document.getElementById('searchInput').value = word; filterNews(word); }}
        document.getElementById('searchInput').oninput=(e)=>filterNews(e.target.value);
        function copyToClipboard(t){{navigator.clipboard.writeText(t).then(()=>alert('Kopiert!'));}}
    </script></body></html>"""

def main():
    db = load_db(); editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=11) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = [i for r in res for i in r]
    # Sortierung aller Items nach Zeit vor der Gruppierung
    raw_sorted = sorted(items, key=lambda x: x["published_iso"], reverse=True)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(raw_sorted, editorial))

if __name__ == "__main__": main()