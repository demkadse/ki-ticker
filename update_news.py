#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
EDITORIAL_FILE = "editorial.json"
# Ein sicheres Fallback-Bild
HERO_IMG_URL = "https://images.unsplash.com/photo-1620712943543-bcc4628c9456?q=80&w=2000&auto=format&fit=crop"

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
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    # Startseite (Root) und Unterseiten
    for p in ["", "ueber-uns.html", "impressum.html", "datenschutz.html"]:
        loc = f"{SITE_URL}/{p}" if p else SITE_URL
        xml += f'  <url><loc>{loc}</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

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

def render_index(items, editorial):
    now_year = datetime.datetime.now().year
    
    # 1. Daten sortieren und gruppieren
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["pub"] if grouped[s] else 0, reverse=True)
    
    # 2. Buttons generieren
    nav_buttons = "".join([f'<button class="nav-btn" onclick="filterFeed(\'{s}\')">{s}</button>' for s in sorted_sources])

    # 3. Editorial HTML
    editorial_html = ""
    if editorial:
        yt_id = parse_qs(urlparse(editorial.get('video_url', '')).query).get('v', [None])[0]
        video_embed = f'<div class="video-box"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        
        editorial_html = f"""
        <article class="editorial">
            <span class="badge">Top-Thema</span>
            <h2>{editorial.get('title')}</h2>
            {video_embed}
            <div class="editorial-text">{editorial.get('description')}</div>
        </article>
        """

    # 4. Feed Sections generieren
    feeds_html = ""
    for idx, source in enumerate(sorted_sources):
        cards_html = ""
        domain = grouped[source][0]['domain']
        
        for item in grouped[source]:
            date_str = item["pub"].strftime("%d.%m. %H:%M")
            cards_html += f"""
            <div class="card" data-src="{source}">
                <img src="{HERO_IMG_URL}" class="card-img" loading="lazy">
                <div class="card-body">
                    <div class="card-date">{date_str}</div>
                    <h3 class="card-title"><a href="{item['url']}" target="_blank">{item['title']}</a></h3>
                    <button class="copy-btn" onclick="copyLink('{item['url']}')">Link kopieren</button>
                </div>
            </div>
            """
        
        feeds_html += f"""
        <section class="feed-section" id="feed-{idx}">
            <div class="feed-header">
                <img src="https://www.google.com/s2/favicons?domain={domain}&sz=32" class="feed-icon">
                <h2 class="feed-title">{source}</h2>
            </div>
            <div class="carousel" id="track-{idx}">
                {cards_html}
            </div>
        </section>
        """

    # 5. Finale HTML Ausgabe
    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
</head>
<body>

    <header class="hero-header">
        <img src="{HERO_IMG_URL}" class="hero-bg-img" alt="Background">
        <div class="hero-content">
            <h1 class="hero-title">{SITE_TITLE}</h1>
            <input type="text" id="searchInput" class="hero-search" placeholder="News filtern...">
            <div class="hero-nav">
                <button class="nav-btn" onclick="resetFilter()">Alle</button>
                {nav_buttons}
            </div>
        </div>
    </header>

    <div class="container">
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
    
    // Filter Logik
    function filterFeed(sourceName) {{
        document.querySelectorAll('.feed-section').forEach(sec => {{
            const title = sec.querySelector('.feed-title').innerText;
            sec.style.display = title === sourceName ? 'block' : 'none';
        }});
    }}

    function resetFilter() {{
        document.querySelectorAll('.feed-section').forEach(sec => sec.style.display = 'block');
    }}

    // Suche
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
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(items, editorial))
    generate_sitemap()

if __name__ == "__main__": main()