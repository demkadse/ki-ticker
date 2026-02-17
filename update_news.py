#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, hashlib, json, re
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor
import requests, feedparser

# --- KONFIGURATION ---
SITE_TITLE = "KI‑Ticker"
SITE_DESC = "Echtzeit-Updates aus der Welt der KI"
SITE_URL = "https://ki-ticker.boehmonline.space"
ADSENSE_PUB = "pub-2616688648278798"
ADSENSE_SLOT = "8395864605"

# WebP optimiertes Fallback für PageSpeed
HERO_IMG = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&q=80&w=800&fm=webp"

DB_FILE = "news_db.json"
DAYS_TO_KEEP = 7
MAX_PER_SOURCE = 8 

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

def save_db(data):
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS_TO_KEEP)
    filtered = [i for i in data if datetime.datetime.fromisoformat(i["published_iso"]) > cutoff]
    with open(DB_FILE, "w", encoding="utf-8") as f: json.dump(filtered[:500], f, ensure_ascii=False, indent=2)

def generate_sitemap():
    pages = [{"loc": "", "p": "1.0"}, {"loc": "impressum.html", "p": "0.3"}, {"loc": "datenschutz.html", "p": "0.3"}]
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p in pages:
        sitemap += f'  <url><loc>{SITE_URL}/{p["loc"]}</loc><priority>{p["p"]}</priority></url>\n'
    sitemap += '</urlset>'
    with open("sitemap.xml", "w", encoding="utf-8") as f: f.write(sitemap)

def extract_image(e):
    ignore_list = ["favicon", "logo", "icon", "avatar", "badge", "mark", "signet"]
    for tag in ["media_content", "media_thumbnail", "links"]:
        items = e.get(tag, [])
        if isinstance(items, list):
            for item in items:
                url = item.get("url") or item.get("href")
                if url and any(ext in url.lower() for ext in [".jpg", ".png", ".jpeg", ".webp"]):
                    if not any(word in url.lower() for word in ignore_list):
                        return url
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

def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    categories = sorted(list(set(it["source"] for it in items)))
    cat_html = '<button class="cat-btn active" onclick="filterCat(\'all\', this)">Alle</button>'
    for c in categories:
        cat_html += f'<button class="cat-btn" onclick="filterCat(\'{c}\', this)">{c}</button>'

    html_content = ""
    for idx, it in enumerate(items[:120]):
        prio = 'fetchpriority="high" loading="eager"' if idx < 3 else 'loading="lazy"'
        src_low = it["source"].lower()
        
        if "arxiv" in src_low or "heise" in src_low:
            img_url = HERO_IMG
        else:
            img_url = it.get("image") if it.get("image") and it.get("image").startswith("http") else HERO_IMG
            
        dt = datetime.datetime.fromisoformat(it["published_iso"])
        html_content += f"""
        <article class="card" data-source="{it["source"]}" data-content="{it["title"].lower()}">
          <div class="img-container">
            <img src="{img_url}" {prio} alt="" onerror="this.onerror=null;this.src='{HERO_IMG}';">
          </div>
          <div class="card-body">
            <div class="meta">
                <img src="https://www.google.com/s2/favicons?domain={it["domain"]}&sz=32" class="source-icon" loading="lazy" width="16" height="16" alt="">
                {it["source"]} • {dt.strftime("%H:%M")}
            </div>
            <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
            <div class="share-bar"><button onclick="copyToClipboard('{it["url"]}')">🔗 Link</button></div>
          </div>
        </article>"""
        if (idx + 1) % 12 == 0:
            html_content += f'<div class="ad-container"><ins class="adsbygoogle" style="display:block" data-ad-format="auto" data-full-width-responsive="true" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title><link rel="icon" type="image/svg+xml" href="favicon.svg">
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{ADSENSE_PUB}" crossorigin="anonymous"></script></head>
    <body class="dark-mode"><main class="container">
        <header class="header">
            <h1>KI‑Ticker</h1>
            <div class="controls">
                <input type="text" id="searchInput" placeholder="Suchen..." aria-label="Suche">
                <div class="category-bar">{cat_html}</div>
            </div>
        </header>
        <div class="news-grid">{html_content}</div>
        <footer class="footer"><p>&copy; {now.year} KI‑Ticker | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p></footer></main>
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
    with ThreadPoolExecutor(max_workers=7) as ex: res = list(ex.map(fetch_feed, FEEDS))
    items = [i for r in res for i in r]
    raw_sorted = sorted({i['url']: i for i in (db + items)}.values(), key=lambda x: x["published_iso"], reverse=True)
    final_items = []
    source_counts = {}
    for it in raw_sorted:
        src = it["source"]
        source_counts[src] = source_counts.get(src, 0) + 1
        if source_counts[src] <= MAX_PER_SOURCE:
            final_items.append(it)
    save_db(final_items)
    generate_sitemap()
    with open("index.html", "w", encoding="utf-8") as f: f.write(render_index(final_items))

if __name__ == "__main__": main()
