#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# --- STEUERUNG VON IMPORTS ---
import os, time, datetime, hashlib, json, re, html
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import requests, feedparser

# --- STEUERUNG VON KONFIGURATION ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
DB_FILE = "news_db.json"
EDITORIAL_FILE = "editorial.json"
HERO_BASE = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80"

# --- STEUERUNG VON DATENQUELLEN ---
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

# --- STEUERUNG VON DATEN-LOADING ---
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

# --- STEUERUNG VON HILFSFUNKTIONEN ---
def get_youtube_id(url):
    if not url: return None
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be': return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch': return parse_qs(parsed.query).get('v', [None])[0]
        if parsed.path.startswith(('/embed/', '/v/')): return parsed.path.split('/')[2]
    return None

def generate_sitemap():
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    xml = f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>{SITE_URL}/index.html</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url><url><loc>{SITE_URL}/ueber-uns.html</loc><lastmod>{now}</lastmod></url></urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

# --- STEUERUNG VON FEED-ABRUF ---
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
            out.append({"title": e.get("title", "").strip(), "url": link, "source": name, "published_iso": dt.isoformat(), "domain": urlparse(link).netloc.replace("www.", "")})
        return out
    except: return []

# --- STEUERUNG VON HTML-RENDERING ---
def render_index(items, editorial):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    hero_default = f"{HERO_BASE}&w=800"
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["published_iso"], reverse=True)

    # Dynamische Kategorie-Buttons
    cat_buttons = ""
    for src in sorted_sources:
        cat_buttons += f'<button class="nav-btn category-btn" onclick="applySearch(\'{src}\')">{src}</button>'
    
    category_html = f'<div class="category-nav-wrapper">{cat_buttons}</div>'

    editorial_html = ""
    if editorial:
        yt_id = get_youtube_id(editorial.get('video_url'))
        author_link = f'<a href="{editorial.get("author_url")}" target="_blank" style="font-size:0.85rem;"><i class="fa-brands fa-youtube"></i> Zum Kanal des Video-Urhebers</a>' if editorial.get('author_url') else ""
        video_embed = f'<div class="video-container"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        
        editorial_html = f"""
        <section class="editorial-section">
            <div class="editorial-badge"><i class="fa-solid fa-star"></i> Tagesthema der Redaktion</div>
            <div class="editorial-card">
                <h2 style="margin-bottom:20px;">{editorial.get('title', '...')}</h2>
                {video_embed}
                <div style="margin-bottom:25px; padding:12px; background:rgba(255,255,255,0.03); border-radius:8px;">
                    {author_link}
                    <p style="font-size:0.75rem; color:var(--muted); margin-top:5px;">Hinweis: Externer Videobeitrag.</p>
                </div>
                
                <div class="editorial-text">{editorial.get('description', '')}</div>
                
                <div class="editorial-footer-area">
                    <div class="sources-box-compact">
                        <strong>Quellen:</strong>
                        <div class="editorial-sources-list">
                            {editorial.get('content', '')}
                        </div>
                    </div>
                    
                    <button class="filter-action-btn-styled" onclick="applySearch('{editorial.get('search_term','')}');">
                        <i class="fa-solid fa-magnifying-glass"></i> Passende News finden
                    </button>
                </div>
            </div>
        </section>"""

    main_content = ""
    for idx, src in enumerate(sorted_sources):
        carousel_id = f"carousel-{idx}"
        cards_html = ""
        source_domain = grouped[src][0]['domain']
        for it in grouped[src]:
            dt = datetime.datetime.fromisoformat(it["published_iso"])
            cards_html += f"""
            <article class="card" data-content="{it["title"].lower()}">
                <div class="img-container"><img src="{hero_default}" loading="lazy" alt=""></div>
                <div class="card-body">
                    <div class="meta">{dt.strftime("%d.%m. • %H:%M")}</div>
                    <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
                    <div class="share-bar">
                        <button class="card-link-btn" onclick="copyToClipboard('{it['url']}')">
                            <i class="fa-solid fa-link"></i> Link kopieren
                        </button>
                    </div>
                </div>
            </article>"""

        main_content += f"""
        <section class="source-section">
            <div class="source-header">
                <div class="source-title"><img src="https://www.google.com/s2/favicons?domain={source_domain}&sz=32" alt=""> {src}</div>
                <div class="carousel-nav">
                    <button class="nav-btn" onclick="scrollCarousel('{carousel_id}', -1)"><i class="fa-solid fa-chevron-left"></i></button>
                    <button class="nav-btn" onclick="scrollCarousel('{carousel_id}', 1)"><i class="fa-solid fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="carousel-wrapper"><div class="news-carousel" id="{carousel_id}">{cards_html}</div></div>
        </section>"""

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{SITE_TITLE}</title><link rel="icon" type="image/svg+xml" href="favicon.svg"><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"><link rel="stylesheet" href="style.css?v={int(time.time())}"></head><body class="dark-mode"><div class="site-layout"><main class="container"><header class="header"><h1>KI‑Ticker</h1><div class="search-wrapper"><input type="text" id="searchInput" placeholder="Feed durchsuchen..."></div>{category_html}</header>{editorial_html}{main_content}<footer class="footer"><p>&copy; {now_dt.year} KI‑Ticker | <a href="ueber-uns.html">Über uns</a> | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p></footer></main></div><script>function scrollCarousel(id, dir) {{ const c = document.getElementById(id); const amount = c.offsetWidth * 0.8; c.scrollBy({{ left: dir * amount, behavior: 'smooth' }}); }} function filterNews(t){{ const v = t.toLowerCase(); document.querySelectorAll('.card').forEach(el => {{ if(el.getAttribute('data-content')) el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none'; }}); }} function applySearch(word) {{ document.getElementById('searchInput').value = word; filterNews(word); window.scrollTo({{top: 0, behavior: 'smooth'}}); }} document.getElementById('searchInput').oninput=(e)=>filterNews(e.target.value); function copyToClipboard(t){{navigator.clipboard.writeText(t).then(()=>alert('Link kopiert!'));}}</script></body></html>"""

# --- STEUERUNG VON HAUPTPROZESS ---
def main():
    db = load_db(); editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=11) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = [i for r in res for i in r]
    raw_sorted = sorted(items, key=lambda x: x["published_iso"], reverse=True)
    generate_sitemap()
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(raw_sorted, editorial))

if __name__ == "__main__": main()