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
DAYS_TO_KEEP = 7
MAX_PER_SOURCE = 6 

FEEDS = [
    ("The Verge AI", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/tag/artificial-intelligence/"),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("Heise KI", "https://www.heise.de/thema/KI/rss.xml"),
    ("arXiv", "https://export.arxiv.org/rss/cs.AI"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("AWS ML Blog", "https://aws.amazon.com/blogs/machine-learning/feed/"),
    ("NVIDIA Blog", "https://blogs.nvidia.com/feed/"),
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
    """Extrahiert die YouTube ID für das Embedding."""
    if not url: return None
    parsed = urlparse(url)
    if parsed.hostname == 'youtu.be': return parsed.path[1:]
    if parsed.hostname in ('www.youtube.com', 'youtube.com'):
        if parsed.path == '/watch': return parse_qs(parsed.query).get('v', [None])[0]
        if parsed.path.startswith(('/embed/', '/v/')): return parsed.path.split('/')[2]
    return None

def save_db(data):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_TO_KEEP)
    filtered = [i for i in data if datetime.datetime.fromisoformat(i["published_iso"]) > cutoff]
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(filtered[:500], f, ensure_ascii=False, indent=2)

def extract_image(e):
    ignore = ["favicon", "logo", "icon", "avatar", "badge"]
    for tag in ["media_content", "media_thumbnail", "links"]:
        items = e.get(tag, [])
        if isinstance(items, list):
            for item in items:
                url = item.get("url") or item.get("href")
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                    if not any(w in url.lower() for w in ignore): return url
    return ""

def fetch_feed(feed_info):
    name, url = feed_info
    try:
        resp = requests.get(url, timeout=15)
        fp = feedparser.parse(resp.content)
        out = []
        for e in fp.entries:
            link = (e.get("link") or "").strip()
            if not link: continue
            ts = e.get("published_parsed") or e.get("updated_parsed")
            dt = datetime.datetime.fromtimestamp(time.mktime(ts), datetime.timezone.utc) if ts else datetime.datetime.now(datetime.timezone.utc)
            out.append({
                "id": hashlib.md5(link.encode()).hexdigest()[:12],
                "title": e.get("title", "").strip(), 
                "url": link, "source": name, "published_iso": dt.isoformat(),
                "domain": urlparse(link).netloc.replace("www.", ""),
                "image": extract_image(e)
            })
        return out
    except: return []

def generate_sitemap(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    news_cutoff = now - datetime.timedelta(hours=48)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">\n'
    xml += f'  <url><loc>{SITE_URL}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>\n'
    for it in items:
        pub_dt = datetime.datetime.fromisoformat(it["published_iso"])
        if pub_dt > news_cutoff:
            title_esc = html.escape(it["title"])
            xml += f'  <url><loc>{it["url"]}</loc><news:news><news:publication><news:name>{SITE_TITLE}</news:name><news:language>de</news:language></news:publication><news:publication_date>{it["published_iso"]}</news:publication_date><news:title>{title_esc}</news:title></news:news></url>\n'
    xml += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(xml)

def render_index(items, editorial):
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    categories = sorted(list(set(it["source"] for it in items)))
    cat_html = "".join([f'<button class="cat-btn" onclick="filterCat(\'{c}\', this)">{c}</button>' for c in categories])
    hero_default = f"{HERO_BASE}&w=1200"

    # Redaktions-Block mit Video-Unterstützung
    editorial_html = ""
    if editorial:
        yt_id = get_youtube_id(editorial.get('video_url'))
        video_embed = ""
        if yt_id:
            video_embed = f"""
            <div class="video-container">
                <iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" 
                        title="YouTube video player" frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" 
                        allowfullscreen></iframe>
            </div>
            """
        
        editorial_html = f"""
        <section class="editorial-section">
            <div class="editorial-badge">Tagesthema der Redaktion</div>
            <div class="editorial-card">
                <h2>{editorial.get('title', 'Titel wird geladen...')}</h2>
                {video_embed}
                <div class="editorial-text">{editorial.get('content', '')}</div>
                <div class="editorial-date">Stand: {editorial.get('date', now_dt.strftime('%d.%m.%Y'))}</div>
            </div>
        </section>
        """

    schema_items = []
    html_content = ""

    for idx, it in enumerate(items[:120]):
        prio = 'fetchpriority="high" loading="eager"' if idx < 2 else 'loading="lazy"'
        src_low = it["source"].lower()
        current_img = it.get("image")
        is_fallback = "arxiv" in src_low or "heise" in src_low or not current_img
        
        if is_fallback:
            img_html = f'<img src="{hero_default}" srcset="{HERO_BASE}&w=300 300w, {HERO_BASE}&w=600 600w" sizes="(max-width: 600px) 300px, 600px" {prio} alt="">'
            schema_images = [f"{HERO_BASE}&w=1000&h=1000", f"{HERO_BASE}&w=1000&h=750", f"{HERO_BASE}&w=1200&h=675"]
        else:
            img_html = f'<img src="{current_img}" {prio} alt="" onerror="this.onerror=null;this.src=\'{hero_default}\';">'
            schema_images = [current_img]
            
        dt = datetime.datetime.fromisoformat(it["published_iso"])
        
        html_content += f"""
        <article class="card" data-source="{it["source"]}" data-content="{it["title"].lower()}">
          <div class="img-container">{img_html}</div>
          <div class="card-body">
            <div class="meta">
                <img src="https://www.google.com/s2/favicons?domain={it["domain"]}&sz=32" class="source-icon" loading="lazy" width="16" height="16" alt="">
                {it["source"]} • {dt.strftime("%H:%M")}
            </div>
            <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
            <div class="share-bar"><button onclick="copyToClipboard('{it['url']}')">🔗 Link</button></div>
          </div>
        </article>"""

        schema_items.append({
            "@type": "ListItem", "position": idx + 1,
            "item": {
                "@type": "NewsArticle", "headline": it["title"][:110], "image": schema_images,
                "datePublished": it["published_iso"], "dateModified": it["published_iso"],
                "author": [{"@type": "Organization", "name": it["source"], "url": f"https://{it['domain']}"}],
                "publisher": {"@type": "Organization", "name": SITE_TITLE, "logo": {"@type": "ImageObject", "url": f"{SITE_URL}/favicon.svg"}},
                "url": it["url"]
            }
        })

        if (idx + 1) % 12 == 0:
            html_content += f'<div class="ad-container"><ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT_FEED}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'

    schema_json = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "itemListElement": schema_items}, ensure_ascii=False)

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title><link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
    <script type="application/ld+json">{schema_json}</script>
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{ADSENSE_PUB}" crossorigin="anonymous"></script></head>
    <body class="dark-mode">
    <div class="site-layout">
        <aside class="sidebar-ad left">
            <ins class="adsbygoogle" style="display:inline-block;width:160px;height:600px" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT_LEFT}"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </aside>
        <main class="container">
            <header class="header">
                <h1>KI‑Ticker</h1>
                <p class="subtitle">Neues aus der Welt der künstlichen Intelligenz</p>
                <div class="controls">
                    <input type="text" id="searchInput" placeholder="Suchen..." aria-label="Suche">
                    <div class="category-bar"><button class="cat-btn active" onclick="filterCat('all', this)">Alle</button>{cat_html}</div>
                </div>
            </header>

            {editorial_html}

            <div class="news-grid">{html_content}</div>
            <footer class="footer"><p>&copy; {now_dt.year} KI‑Ticker | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p></footer>
        </main>
        <aside class="sidebar-ad right">
            <ins class="adsbygoogle" style="display:inline-block;width:160px;height:600px" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT_RIGHT}"></ins>
            <script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>
        </aside>
    </div>
    <script>
        function filterCat(cat, btn) {{
            document.querySelectorAll('.cat-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            document.querySelectorAll('.card').forEach(el => {{
                el.style.display = (cat === 'all' || el.getAttribute('data-source') === cat) ? 'flex' : 'none';
            }});
        }}
        function filterNews(t){{
            const v = t.toLowerCase();
            document.querySelectorAll('.card').forEach(el => {{
                el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none';
            }});
        }}
        document.getElementById('searchInput').oninput=(e)=>filterNews(e.target.value);
        function copyToClipboard(t){{navigator.clipboard.writeText(t).then(()=>alert('Kopiert!'));}}
    </script></body></html>"""

def main():
    db = load_db()
    editorial = load_editorial()
    with ThreadPoolExecutor(max_workers=7) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = [i for r in res for i in r]
    raw_sorted = sorted({i['url']: i for i in (db + items)}.values(), key=lambda x: x["published_iso"], reverse=True)
    final_items = []
    source_counts = {}
    for it in raw_sorted:
        src = it["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts[src] <= MAX_PER_SOURCE: final_items.append(it)
    save_db(final_items)
    generate_sitemap(final_items)
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(final_items, editorial))

if __name__ == "__main__": main()