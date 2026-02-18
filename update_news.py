#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
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
]

def load_editorial():
    if os.path.exists(EDITORIAL_FILE):
        try:
            with open(EDITORIAL_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return None
    return None

def generate_sitemap():
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    # Liste der zu indizierenden Seiten
    pages = [
        ("index.html", "1.0"),
        ("ueber-uns.html", "0.5"),
        ("impressum.html", "0.5"),
        ("datenschutz.html", "0.5")
    ]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p, prio in pages:
        xml += f'  <url>\n    <loc>{SITE_URL}/{p}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>{prio}</priority>\n  </url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

def fetch_feed(info):
    name, url = info
    try:
        resp = requests.get(url, timeout=15)
        fp = feedparser.parse(resp.content)
        return [{"title": e.get("title", "").strip(), "url": e.get("link", "").strip(), "source": name, "pub": e.get("published_parsed") or e.get("updated_parsed"), "domain": urlparse(e.get("link")).netloc.replace("www.", "")} for e in fp.entries]
    except: return []

def render_index(items, editorial):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    sorted_src = sorted(grouped.keys(), key=lambda s: time.mktime(grouped[s][0]["pub"]) if grouped[s][0]["pub"] else 0, reverse=True)
    cat_btns = "".join([f'<button class="cat-btn" onclick="applySearch(\'{s}\')">{s}</button>' for s in sorted_src])

    editorial_html = ""
    if editorial:
        yt_id = parse_qs(urlparse(editorial.get('video_url', '')).query).get('v', [None])[0]
        video = f'<div class="video-container"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        editorial_html = f"""<article class="editorial-card"><div class="editorial-badge">Top-Thema</div><h2>{editorial.get('title')}</h2>{video}<div class="editorial-text" id="eWrap">{editorial.get('description')}<div class="read-more-overlay"></div></div><button class="toggle-btn" id="tBtn" onclick="toggleE()">Analyse vollständig lesen</button></article>"""

    main_html = ""
    for idx, s in enumerate(sorted_src):
        cards = ""
        for it in grouped[s]:
            dt = datetime.datetime.fromisoformat(datetime.datetime.fromtimestamp(time.mktime(it["pub"])).isoformat()).strftime("%d.%m. • %H:%M") if it["pub"] else ""
            cards += f"""
            <article class="news-card" data-content="{it['title'].lower()}">
                <img src="{HERO_BASE}&w=800" alt="">
                <div class="card-body">
                    <div style="font-size:11px; color:var(--muted); margin-bottom:10px;">{dt}</div>
                    <h3><a href="{it['url']}" target="_blank">{it['title']}</a></h3>
                    <button class="cat-btn" style="width:100%; margin-top:auto;" onclick="copyToClipboard('{it['url']}')">Link kopieren</button>
                </div>
            </article>"""
        
        main_html += f"""
        <section class="news-row">
            <div class="source-header">
                <div class="source-title"><img src="https://www.google.com/s2/favicons?domain={grouped[s][0]['domain']}&sz=32"> {s}</div>
                <div class="carousel-nav">
                    <button class="nav-btn" onclick="scrollC('c-{idx}', -1)"><i class="fa-solid fa-chevron-left"></i></button>
                    <button class="nav-btn" onclick="scrollC('c-{idx}', 1)"><i class="fa-solid fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="news-grid" id="c-{idx}">{cards}</div>
        </section>"""

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="style.css?v={int(time.time())}"></head><body>
    <header class="hero-header" id="siteHeader">
        <h1>KI‑Ticker</h1>
        <div class="header-controls">
            <input type="text" id="searchInput" placeholder="Feed durchsuchen...">
            <div class="category-bar">{cat_btns}</div>
        </div>
    </header>
    <div class="main-layout">
        <main>
            {editorial_html}
            {main_html}
        </main>
    </div>
    <footer class="site-footer">&copy; {now_dt.year} KI‑Ticker | <a href="ueber-uns.html">Über uns</a> | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></footer>
    <script>
    function scrollC(id, d) {{ const c = document.getElementById(id); c.scrollBy({{ left: d * 360, behavior: 'smooth' }}); }}
    function filterN(t) {{ const v = t.toLowerCase(); document.querySelectorAll('.news-card').forEach(el => {{ el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none'; }}); }}
    function toggleE() {{ const w = document.getElementById('eWrap'); const b = document.getElementById('tBtn'); w.classList.toggle('expanded'); b.innerText = w.classList.contains('expanded') ? 'Zusammenklappen' : 'Analyse vollständig lesen'; }}
    function applySearch(w) {{ document.getElementById('searchInput').value = w; filterN(w); window.scrollTo({{top: 400, behavior: 'smooth'}}); }}
    document.getElementById('searchInput').oninput = (e) => filterN(e.target.value);
    function copyToClipboard(u) {{ navigator.clipboard.writeText(u).then(() => alert('Link kopiert!')); }}
    </script></body></html>"""

def main():
    editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=11) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = sorted([i for r in res for i in r], key=lambda x: time.mktime(x["pub"]) if x["pub"] else 0, reverse=True)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(items, editorial))
    generate_sitemap()

if __name__ == "__main__": main()