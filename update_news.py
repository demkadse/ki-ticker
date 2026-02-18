#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
EDITORIAL_FILE = "editorial.json"
HERO_IMG = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=600"

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

def fetch_feed(info):
    name, url = info
    try:
        resp = requests.get(url, timeout=10)
        fp = feedparser.parse(resp.content)
        items = []
        for e in fp.entries:
            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)
            items.append({
                "title": e.get("title", "").strip(),
                "url": e.get("link", "").strip(),
                "source": name,
                "pub": dt,
                "domain": urlparse(e.get("link", "")).netloc.replace("www.", "")
            })
        return items
    except: return []

def generate_sitemap():
    now = datetime.datetime.now().strftime("%Y-%m-%d")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in ["", "ueber-uns.html", "impressum.html", "datenschutz.html"]:
        loc = f"{SITE_URL}/{p}" if p else SITE_URL
        xml += f'  <url><loc>{loc}</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

def render_html(items, editorial):
    now_year = datetime.datetime.now().year
    
    # 1. Group & Sort
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["pub"] if grouped[s] else 0, reverse=True)
    
    # 2. Buttons (Klasse: btn)
    nav_buttons = "".join([f'<button class="btn" onclick="filterFeed(\'{s}\')">{s}</button>' for s in sorted_sources])

    # 3. Editorial Box (Klasse: editorial-box)
    editorial_html = ""
    if editorial:
        yt_id = parse_qs(urlparse(editorial.get('video_url', '')).query).get('v', [None])[0]
        video_embed = f'<div class="video-wrapper"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        
        sources_text = editorial.get('content', 'Keine Quellen angegeben.')
        
        editorial_html = f"""
        <article class="editorial-box">
            <span class="editorial-badge">Top-Thema der Redaktion</span>
            <h2 class="editorial-title">{editorial.get('title')}</h2>
            {video_embed}
            <div class="editorial-content">{editorial.get('description')}</div>
            <div class="editorial-sources">
                <strong>Quellen & Referenzen:</strong>
                {sources_text}
            </div>
        </article>
        """

    # 4. News Feeds
    feeds_html = ""
    for idx, source in enumerate(sorted_sources):
        cards = ""
        domain = grouped[source][0]['domain']
        
        for item in grouped[source]:
            date_str = item["pub"].strftime("%d.%m. %H:%M")
            cards += f"""
            <article class="card" data-src="{source}">
                <img src="{HERO_IMG}" class="card__img" loading="lazy">
                <div class="card__body">
                    <div class="card__meta">{date_str}</div>
                    <h3 class="card__title"><a href="{item['url']}" target="_blank">{item['title']}</a></h3>
                    <button class="btn btn--copy" onclick="copyLink('{item['url']}')">Link kopieren</button>
                </div>
            </article>
            """
        
        feeds_html += f"""
        <section class="section-wrapper" id="feed-{idx}">
            <div class="section-header">
                <img src="https://www.google.com/s2/favicons?domain={domain}&sz=64" class="section-icon">
                <h2 class="section-title">{source}</h2>
            </div>
            <div class="carousel" id="track-{idx}">
                {cards}
            </div>
        </section>
        """

    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
</head>
<body>

    <header class="header">
        <h1 class="header__title">{SITE_TITLE}</h1>
        <input type="text" id="searchInput" class="header__search" placeholder="News durchsuchen...">
        <div class="nav-wrapper">
            <button class="btn" onclick="resetFilter()">Alle Anzeigen</button>
            {nav_buttons}
        </div>
    </header>

    <div class="main-container">
        <main>
            {editorial_html}
            <div id="feedContainer">
                {feeds_html}
            </div>
        </main>
    </div>

    <footer class="footer">
        <p>&copy; {now_year} {SITE_TITLE}</p>
        <div style="margin-top:10px;">
            <a href="ueber-uns.html">Über uns</a>
            <a href="impressum.html">Impressum</a>
            <a href="datenschutz.html">Datenschutz</a>
        </div>
    </footer>

    <script>
    const searchInput = document.getElementById('searchInput');
    
    function filterFeed(sourceName) {{
        document.querySelectorAll('.section-wrapper').forEach(sec => {{
            const title = sec.querySelector('.section-title').innerText.trim();
            sec.style.display = title.includes(sourceName) ? 'block' : 'none';
        }});
    }}

    function resetFilter() {{
        document.querySelectorAll('.section-wrapper').forEach(sec => sec.style.display = 'block');
    }}

    searchInput.addEventListener('input', (e) => {{
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.card').forEach(card => {{
            const txt = card.innerText.toLowerCase();
            card.style.display = txt.includes(term) ? 'flex' : 'none';
        }});
    }});

    function copyLink(url) {{
        navigator.clipboard.writeText(url).then(() => alert('Link kopiert!'));
    }}
    </script>
</body>
</html>"""

def main():
    editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=10) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = sorted([i for r in res for i in r], key=lambda x: x["pub"], reverse=True)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_html(items, editorial))
    generate_sitemap()

if __name__ == "__main__": main()