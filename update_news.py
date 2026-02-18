#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
DB_FILE = "news_db.json"
EDITORIAL_FILE = "editorial.json"
HERO_BASE = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80"

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

def load_editorial():
    if os.path.exists(EDITORIAL_FILE):
        try:
            with open(EDITORIAL_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

def generate_sitemap():
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    pages = ["index.html", "ueber-uns.html", "impressum.html", "datenschutz.html"]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        xml += f'  <url><loc>{SITE_URL}/{p}</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

def fetch_feed(info):
    name, url = info
    try:
        resp = requests.get(url, timeout=15)
        fp = feedparser.parse(resp.content)
        items = []
        for e in fp.entries:
            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)
            items.append({
                "title": e.get("title", "").strip(),
                "url": e.get("link", "").strip(),
                "source": name,
                "published_iso": dt.isoformat(),
                "domain": urlparse(e.get("link")).netloc.replace("www.", "")
            })
        return items
    except: return []

def render_index(items, editorial):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["published_iso"], reverse=True)
    cat_buttons = "".join([f'<button class="category-btn" onclick="applySearch(\'{s}\')">{s}</button>' for s in sorted_sources])

    editorial_html = ""
    if editorial:
        yt_url = editorial.get('video_url', '')
        parsed_yt = urlparse(yt_url)
        yt_id = parse_qs(parsed_yt.query).get('v', [None])[0] if parsed_yt.query else None
        video_embed = f'<div class="video-container"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        
        editorial_html = f"""
        <section class="editorial-section">
            <div class="editorial-card">
                <div class="editorial-badge">Top-Thema</div>
                <h2 style="margin-bottom:25px; font-size:2rem;">{editorial.get('title')}</h2>
                {video_embed}
                <div style="margin-bottom:30px; padding:15px; background:rgba(255,255,255,0.03); border-radius:8px;">
                    <a href="{editorial.get('author_url')}" target="_blank" style="font-size:0.9rem;"><i class="fa-brands fa-youtube"></i> Zum Urheber</a>
                </div>
                <div class="editorial-expand-wrapper" id="eWrap">
                    <div class="editorial-text">{editorial.get('description')}</div>
                    <div class="read-more-overlay"></div>
                </div>
                <button class="toggle-btn" id="tBtn" onclick="toggleE()">Analyse vollständig lesen</button>
                <div class="editorial-footer-area">
                    <div class="sources-box-compact">
                        <strong>Quellen:</strong>
                        <div class="editorial-sources-list">{editorial.get('content')}</div>
                    </div>
                    <button class="category-btn" style="background:var(--acc); color:var(--bg); border:none;" onclick="applySearch('{editorial.get('search_term')}');">Passende News</button>
                </div>
            </div>
        </section>"""

    main_html = ""
    for idx, s in enumerate(sorted_sources):
        cards = ""
        for it in grouped[s]:
            dt = datetime.datetime.fromisoformat(it["published_iso"]).strftime("%d.%m. • %H:%M")
            cards += f"""
            <article class="card" data-content="{it['title'].lower()}">
                <div class="img-container"><img src="{HERO_BASE}&w=800" alt=""></div>
                <div class="card-body">
                    <div class="meta" style="font-size:11px; color:var(--muted); margin-bottom:10px;">{dt}</div>
                    <h3><a href="{it['url']}" target="_blank">{it['title']}</a></h3>
                    <div class="share-btn-box">
                        <button class="category-btn" style="width:100%;" onclick="copyToClipboard('{it['url']}')">Link kopieren</button>
                    </div>
                </div>
            </article>"""
        
        main_html += f"""
        <section class="source-section">
            <div class="source-header">
                <div class="source-title"><img src="https://www.google.com/s2/favicons?domain={grouped[s][0]['domain']}&sz=32"> {s}</div>
                <div class="carousel-nav">
                    <button class="nav-btn" onclick="scrollC('c-{idx}', -1)"><i class="fa-solid fa-chevron-left"></i></button>
                    <button class="nav-btn" onclick="scrollC('c-{idx}', 1)"><i class="fa-solid fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="news-carousel" id="c-{idx}">{cards}</div>
        </section>"""

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="cache-control" content="no-cache"><title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="style.css?v={int(time.time())}"></head><body>
    <header class="header">
        <h1>KI‑Ticker</h1>
        <div class="header-ui-container">
            <input type="text" id="searchInput" placeholder="Feed durchsuchen...">
            <div class="category-nav-wrapper">{cat_buttons}</div>
        </div>
    </header>
    <div class="site-layout"><main class="container">{editorial_html}{main_html}
    <footer class="footer"><p>&copy; {now_dt.year} KI‑Ticker | <a href="ueber-uns.html">Über uns</a> | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p></footer></main></div>
    <script>
    function scrollC(id, d) {{ const c = document.getElementById(id); c.scrollBy({{ left: d * 400, behavior: 'smooth' }}); }}
    function filterN(t) {{ const v = t.toLowerCase(); document.querySelectorAll('.card').forEach(el => {{ el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none'; }}); }}
    function toggleE() {{ const w = document.getElementById('eWrap'); const b = document.getElementById('tBtn'); w.classList.toggle('expanded'); b.innerText = w.classList.contains('expanded') ? 'Zusammenklappen' : 'Analyse vollständig lesen'; }}
    function applySearch(w) {{ document.getElementById('searchInput').value = w; filterN(w); window.scrollTo({{top: 450, behavior: 'smooth'}}); }}
    document.getElementById('searchInput').oninput = (e) => filterN(e.target.value);
    function copyToClipboard(u) {{ navigator.clipboard.writeText(u).then(() => alert('Link kopiert!')); }}
    </script></body></html>"""

def main():
    editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=11) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = sorted([i for r in res for i in r], key=lambda x: x["published_iso"], reverse=True)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(items, editorial))
    generate_sitemap()

if __name__ == "__main__": main()