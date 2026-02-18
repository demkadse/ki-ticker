#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, time, datetime, json, requests, feedparser
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor

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
    # SEO Fix: index.html wird als Root '/' angegeben
    pages = [("", "1.0"), ("ueber-uns.html", "0.5"), ("impressum.html", "0.5"), ("datenschutz.html", "0.5")]
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for p, prio in pages:
        xml += f'  <url><loc>{SITE_URL}/{p}</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>{prio}</priority></url>\n'
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
        video = f'<div class="video-wrap"><iframe src="https://www.youtube-nocookie.com/embed/{yt_id}" allowfullscreen></iframe></div>' if yt_id else ""
        editorial_html = f"""<article class="editorial-card"><div class="editorial-badge"><i class="fa-solid fa-star"></i> Top-Thema</div><h2>{editorial.get('title')}</h2>{video}<div class="editorial-text">{editorial.get('description')}</div></article>"""

    main_html = ""
    for idx, s in enumerate(sorted_src):
        cards = ""
        for it in grouped[s]:
            dt = datetime.datetime.fromtimestamp(time.mktime(it["pub"])).strftime("%d.%m. • %H:%M") if it["pub"] else ""
            cards += f"""<article class="news-card" data-content="{it['title'].lower()}"><img src="{HERO_BASE}&w=800"><div class="card-body"><div style="font-size:11px; color:#94a3b8; margin-bottom:12px;">{dt}</div><h3><a href="{it['url']}" target="_blank">{it['title']}</a></h3><button class="cat-btn" style="width:100%; margin-top:auto;" onclick="copyToClipboard('{it['url']}')">Link kopieren</button></div></article>"""
        main_html += f"""<section class="source-row"><h2 class="source-title"><img src="https://www.google.com/s2/favicons?domain={grouped[s][0]['domain']}&sz=32"> {s}</h2><div class="carousel-wrapper" id="c-{idx}">{cards}</div></section>"""

    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title><link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <link rel="stylesheet" href="style.css?v={int(time.time())}"></head><body>
    <header id="siteHeader"><h1>KI‑Ticker</h1><div class="search-wrap"><input type="text" id="searchInput" placeholder="Themen oder Quellen suchen..."></div><div class="cat-bar">{cat_btns}</div></header>
    <div class="main-content"><main>{editorial_html}{main_html}</main></div>
    <footer class="site-footer">&copy; {now_dt.year} KI‑Ticker | <a href="ueber-uns.html">Über uns</a> | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></footer>
    <script>
    function filterN(t) {{ const v = t.toLowerCase(); document.querySelectorAll('.news-card').forEach(el => {{ el.style.display = el.getAttribute('data-content').includes(v) ? 'flex' : 'none'; }}); }}
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