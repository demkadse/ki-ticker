
Run python builder/fetch_and_build.py
Traceback (most recent call last):
  File "/home/runner/work/ki-ticker/ki-ticker/builder/fetch_and_build.py", line 638, in <module>
============================================================
    build_all()
  File "/home/runner/work/ki-ticker/ki-ticker/builder/fetch_and_build.py", line 617, in build_all
    render_static_pages()
  File "/home/runner/work/ki-ticker/ki-ticker/builder/fetch_and_build.py", line 449, in render_static_pages
    html = render_template(
           ^^^^^^^^^^^^^^^^
  File "/home/runner/work/ki-ticker/ki-ticker/builder/fetch_and_build.py", line 339, in render_template
    tpl = env.get_template(template_name)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/jinja2/environment.py", line 1013, in get_template
  KI‑Ticker Build gestartet
============================================================
[INFO] Lade Feed: The Verge – AI (https://www.theverge.com/rss/ai-artificial-intelligence/index.xml)
[INFO] Lade Feed: MIT Technology Review – AI (https://www.technologyreview.com/feed/tag/artificial-intelligence/)
[WARN] Feed 'MIT Technology Review – AI' konnte nicht sauber gelesen werden: <unknown>:2:0: syntax error
[INFO] Lade Feed: VentureBeat – AI (https://venturebeat.com/category/ai/feed/)
[WARN] Feed 'VentureBeat – AI' konnte nicht sauber gelesen werden: document declared as us-ascii, but parsed as utf-8
[INFO] Lade Feed: Google AI Blog (https://ai.googleblog.com/atom.xml)
[WARN] Feed 'Google AI Blog' konnte nicht sauber gelesen werden: <unknown>:4:31: mismatched tag
[INFO] Lade Feed: OpenAI (https://openai.com/blog/rss/)
[WARN] Feed 'OpenAI' konnte nicht sauber gelesen werden: <unknown>:4:17: not well-formed (invalid token)
[INFO] Lade Feed: Meta AI (https://ai.facebook.com/blog/rss/)
[WARN] Feed 'Meta AI' konnte nicht sauber gelesen werden: <unknown>:4:1420: not well-formed (invalid token)
[INFO] Lade Feed: NVIDIA Blog – AI (https://blogs.nvidia.com/blog/category/ai/feed/)
[WARN] Feed 'NVIDIA Blog – AI' konnte nicht sauber gelesen werden: <unknown>:62:0: undefined entity
[INFO] Lade Feed: AWS ML Blog (https://aws.amazon.com/blogs/machine-learning/feed/)
[INFO] Lade Feed: arXiv cs.AI (https://export.arxiv.org/rss/cs.AI)
[INFO] Lade Feed: arXiv cs.CL (https://export.arxiv.org/rss/cs.CL)
[INFO] Lade Feed: Papers with Code – Latest (https://paperswithcode.com/feeds/latest)
[WARN] Feed 'Papers with Code – Latest' konnte nicht sauber gelesen werden: <unknown>:2:0: syntax error
[INFO] Roh-Artikel geladen: 117
[INFO] Nach Deduplikation: 114 Artikel
[INFO] Generierte Seiten: 4
[OK] index.html erzeugt
[OK] Seite 1 erzeugt → /home/runner/work/ki-ticker/ki-ticker/public/index.html
[OK] Seite 2 erzeugt → /home/runner/work/ki-ticker/ki-ticker/public/page/2/index.html
[OK] Seite 3 erzeugt → /home/runner/work/ki-ticker/ki-ticker/public/page/3/index.html
[OK] Seite 4 erzeugt → /home/runner/work/ki-ticker/ki-ticker/public/page/4/index.html
[OK] Statische Seite erzeugt → about.html
[OK] Statische Seite erzeugt → impressum.html
    return self._load_template(name, globals)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/jinja2/environment.py", line 972, in _load_template
    template = self.loader.load(self, name, self.make_globals(globals))
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/jinja2/loaders.py", line 138, in load
    code = environment.compile(source, name, filename)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/jinja2/environment.py", line 768, in compile
    self.handle_exception(source=source_hint)
  File "/opt/hostedtoolcache/Python/3.11.14/x64/lib/python3.11/site-packages/jinja2/environment.py", line 939, in handle_exception
    raise rewrite_traceback_stack(source=source)
  File "/home/runner/work/ki-ticker/ki-ticker/builder/templates/datenschutz.html.j2", line 3, in template
    {% block content %}
    ^^^^^^^^^^^^^^^^^^^^
jinja2.exceptions.TemplateSyntaxError: Unexpected end of template. Jinja was looking for the following tags: 'endblock'. The innermost block that needs to be closed is 'block'.
Error: Process completed with exit code 1.
