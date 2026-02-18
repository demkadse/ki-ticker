#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

# --- CONFIG ---
SITE_TITLE = "KI‑Ticker"
SITE_URL = "https://ki-ticker.boehmonline.space"
EDITORIAL_FILE = "editorial.json"
# Fallback-Bild, falls kein Bild gefunden wird (Performance optimiert)
HERO_BASE = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=600"

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
    # Logik: Root hat Prio 1.0, Unterseiten 0.8
    pages = [("", "1.0"), ("ueber-uns.html", "0.8"), ("impressum.html", "0.8"), ("datenschutz.html", "0.8")]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p, prio in pages:
        # Falls p leer ist (Root), kein Slash am Ende, sonst Slash
        loc = f"{SITE_URL}/{p}" if p else SITE_URL
        xml += f'  <url>\n    <loc>{loc}</loc>\n    <lastmod>{now}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>{prio}</priority>\n  </url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

def fetch_feed(info):
    name, url = info
    try:
        # Timeout verhindert Hänger
        resp = requests.get(url, timeout=10)
        fp = feedparser.parse(resp.content)
        items = []
        for e in fp.entries:
            # Datums-Logik: Versuche published, sonst updated, sonst jetzt
            ts = e.get("published_parsed") or e.get("updated_parsed")
            if ts:
                dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc)
            else:
                dt = datetime.datetime.now(datetime.timezone.utc)
            
            items.append({
                "title": e.get("title", "Kein Titel").strip(),
                "url": e.get("link", "").strip(),
                "source": name,
                "pub": dt,
                "domain": urlparse(e.get("link", "")).netloc.replace("www.", "")
            })
        return items
    except Exception as e:
        print(f"Error fetching {name}: {e}")
        return []

def render_html(items, editorial):
    now_year = datetime.datetime.now().year
    
    # 1. Gruppieren nach Quelle
    grouped = {}
    for it in items:
        if it["source"] not in grouped: grouped[it["source"]] = []
        # Limit auf 10 Items pro Quelle
        if len(grouped[it["source"]]) < 10: grouped[it["source"]].append(it)
    
    # 2. Sortieren der Quellen nach dem aktuellsten Artikel
    sorted_sources = sorted(grouped.keys(), key=lambda s: grouped[s][0]["pub"] if grouped[s] else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc), reverse=True)
    
    # 3. Kategorie-Buttons generieren
    cat_buttons = "".join([f'<button class="cat-btn" onclick="filterSource(\'{s}\')">{s}</button>' for s in sorted_sources])

    # 4. Editorial HTML bauen
    editorial_html = ""
    if editorial:
        # YouTube ID extrahieren (Robust)
        yt_id = None
        if "video_url" in editorial and editorial["video_url"]:
            parsed = urlparse(editorial["video_url"])
            if parsed.query:
                yt_id = parse_qs(parsed.query).get('v', [None])[0]
        
        video_embed = f'<div class="video-frame"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        
        editorial_html = f"""
        <article class="editorial-card">
            <span class="badge">Tagesthema der Redaktion</span>
            <h2>{editorial.get('title', '')}</h2>
            {video_embed}
            <div class="text-content">{editorial.get('description', '')}</div>
        </article>
        """

    # 5. News-Feeds HTML bauen
    feeds_html = ""
    for idx, source in enumerate(sorted_sources):
        cards_html = ""
        domain = grouped[source][0]['domain']
        
        for item in grouped[source]:
            date_str = item["pub"].strftime("%d.%m. %H:%M")
            cards_html += f"""
            <div class="news-card" data-source="{source}">
                <img src="{HERO_BASE}" class="card-img" loading="lazy" alt="News Image">
                <div class="card-content">
                    <div class="card-meta">{date_str}</div>
                    <h3 class="card-title"><a href="{item['url']}" target="_blank">{item['title']}</a></h3>
                    <button class="copy-btn" onclick="copyLink('{item['url']}')">Link kopieren</button>
                </div>
            </div>
            """
        
        feeds_html += f"""
        <section class="news-section" id="src-{idx}">
            <div class="section-header">
                <div class="source-label">
                    <img src="https://www.google.com/s2/favicons?domain={domain}&sz=32" alt="{source}">
                    {source}
                </div>
                <div class="carousel-controls">
                    <button class="nav-arrow" onclick="scrollCarousel('track-{idx}', -1)"><i class="fa-solid fa-chevron-left"></i></button>
                    <button class="nav-arrow" onclick="scrollCarousel('track-{idx}', 1)"><i class="fa-solid fa-chevron-right"></i></button>
                </div>
            </div>
            <div class="carousel-track" id="track-{idx}">
                {cards_html}
            </div>
        </section>
        """

    # 6. Gesamtes HTML zusammensetzen
    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
</head>
<body>

    <header id="siteHeader">
        <h1>{SITE_TITLE}</h1>
        <div class="header-ui">
            <input type="text" id="searchInput" class="search-input" placeholder="Nachrichten filtern...">
            <div class="category-nav">
                <button class="cat-btn" onclick="resetFilter()">Alle</button>
                {cat_buttons}
            </div>
        </div>
    </header>

    <div class="main-container">
        <main>
            {editorial_html}
            <div id="newsContainer">
                {feeds_html}
            </div>
        </main>
    </div>

    <footer class="site-footer">
        <p>&copy; {now_year} {SITE_TITLE} — Kuratiert durch KI & Mensch</p>
        <div class="footer-links">
            <a href="ueber-uns.html">Über uns</a>
            <a href="impressum.html">Impressum</a>
            <a href="datenschutz.html">Datenschutz</a>
        </div>
    </footer>

    <script>
    // Scroll Logic
    function scrollCarousel(id, direction) {{
        const track = document.getElementById(id);
        const scrollAmount = 340; // Kartenbreite + Gap
        track.scrollBy({{ left: direction * scrollAmount, behavior: 'smooth' }});
    }}

    // Search Logic
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', (e) => {{
        const term = e.target.value.toLowerCase();
        document.querySelectorAll('.news-card').forEach(card => {{
            const title = card.querySelector('.card-title').innerText.toLowerCase();
            card.style.display = title.includes(term) ? 'flex' : 'none';
        }});
    }});

    // Category Filter Logic
    function filterSource(sourceName) {{
        // Verstecke alle Sections, die nicht matchen
        document.querySelectorAll('.news-section').forEach(sec => {{
            const label = sec.querySelector('.source-label').innerText.trim();
            sec.style.display = label === sourceName ? 'block' : 'none';
        }});
        // Scroll nach oben zum Content
        document.querySelector('.main-container').scrollIntoView({{ behavior: 'smooth' }});
    }}

    function resetFilter() {{
        document.querySelectorAll('.news-section').forEach(sec => sec.style.display = 'block');
    }}

    // Utility
    function copyLink(url) {{
        navigator.clipboard.writeText(url).then(() => alert('Link in Zwischenablage kopiert!'));
    }}
    </script>
</body>
</html>"""

def main():
    editorial = load_editorial()
    # Paralleles Abrufen der Feeds
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_feed, FEEDS))
    
    # Flatten list
    all_items = [item for sublist in results for item in sublist]
    
    # Sortieren nach Datum (neueste zuerst)
    all_items.sort(key=lambda x: x["pub"], reverse=True)
    
    # HTML generieren
    html_content = render_html(all_items, editorial)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    
    generate_sitemap()
    print("Update erfolgreich.")

if __name__ == "__main__":
    main()