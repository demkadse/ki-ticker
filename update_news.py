def render_index(items):
    now = datetime.datetime.now(datetime.timezone.utc)
    # WICHTIG: Ein Standard-Bild definieren
    DEFAULT_IMG = "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?q=80&w=200&auto=format&fit=crop"
    
    ad_block = f'<div class="ad-container"><ins class="adsbygoogle" style="display:block" data-ad-format="fluid" data-ad-layout-key="-fb+5w+4e-db+86" data-ad-client="ca-{ADSENSE_PUB}" data-ad-slot="{ADSENSE_SLOT}"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script></div>'

    html_content = ""
    for idx, it in enumerate(items[:100]):
        # Prüfen, ob ein Bild-Link vorhanden ist, sonst Standard-Bild
        img_url = it.get("image") if it.get("image") and it.get("image").startswith("http") else DEFAULT_IMG
        dt = datetime.datetime.fromisoformat(it["published_iso"])
        
        html_content += f"""
        <article class="card" data-content="{it["title"].lower()}">
          <div class="img-container">
            <img src="{img_url}" loading="lazy" onerror="this.onerror=null;this.src='{DEFAULT_IMG}';">
          </div>
          <div class="card-body">
            <div>
                <div class="meta">
                    <img src="https://www.google.com/s2/favicons?domain={it["domain"]}&sz=32" class="source-icon">
                    {it["source"]} • {dt.strftime("%H:%M")}
                </div>
                <h3><a href="{it["url"]}" target="_blank">{it["title"]}</a></h3>
            </div>
            <div class="share-bar">
                <button onclick="copyToClipboard('{it["url"]}')">🔗 Link</button>
            </div>
          </div>
        </article>"""
        if (idx + 1) % 8 == 0: html_content += ad_block

    # Der Rest der Funktion bleibt gleich...
    return f"""<!doctype html>
<html lang="de">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{SITE_TITLE}</title>
    <link rel="stylesheet" href="style.css?v={int(time.time())}">
    <script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-{ADSENSE_PUB}" crossorigin="anonymous"></script>
</head>
<body class="dark-mode">
    <header class="header">
        <h1>KI‑Ticker</h1>
        <div class="controls"><input type="text" id="searchInput" placeholder="Suchen..."></div>
    </header>
    <main class="container" id="news-container">{html_content}</main>
    <footer class="footer">
        <p>&copy; {now.year} KI‑Ticker | <a href="impressum.html">Impressum</a> | <a href="datenschutz.html">Datenschutz</a></p>
    </footer>
    <script>
        function filterNews(t) {{
            const val = t.toLowerCase();
            document.querySelectorAll('.card').forEach(el => {{
                // WICHTIG: 'flex' statt 'block' für das neue Layout
                el.style.display = el.getAttribute('data-content').includes(val) ? 'flex' : 'none';
            }});
        }}
        document.getElementById('searchInput').oninput = (e) => filterNews(e.target.value);
        function copyToClipboard(t) {{ navigator.clipboard.writeText(t).then(() => alert('Link kopiert!')); }}
    </script>
</body>
</html>"""
