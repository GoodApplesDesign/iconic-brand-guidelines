"""Builds the guidelines site: _build/src/pages/*.html + layout.html -> /*.html at the repo root.

Run from anywhere:  python3 _build/build.py
Needs: fonttools, uharfbuzz (pip3 install --user fonttools uharfbuzz) and the Sugar Magic font installed in ~/Library/Fonts.

Page source conventions
- First line: <!-- {"title": "Logo", "intro": "..."} -->   (JSON page meta)
- <section id="x" data-nav="Label"> ... </section>         becomes a sidebar sub-link
- <smd>Text</smd>                                           Sugar Magic display: caps, tracking 60 (page titles)
- <sm>Text</sm>                                             Sugar Magic, mixed case (only for 'don't' examples)
- <smc>TEXT</smc>                                           Sugar Magic caps, tracking 100 (section headings, labels)
- <!--include:name-->                                       inlines _build/src/partials/name.svg (made by make_diagrams.py)
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from sugar import sugar_svg  # noqa: E402

PAGES = [  # (slug, nav label) in site order
    ('index', 'Foundations'),
    ('logo', 'Logo'),
    ('colour', 'Colour'),
    ('typography', 'Typography'),
]
SECTION_RE = re.compile(r'<section[^>]*\bid="([^"]+)"[^>]*\bdata-nav="([^"]+)"')


def href(slug):
    return 'index.html' if slug == 'index' else f'{slug}.html'


def sugar(page):
    page = re.sub(r'<smd>(.*?)</smd>', lambda m: sugar_svg(html.unescape(m.group(1)).upper(), 60, 'sm caps display'), page, flags=re.S)
    page = re.sub(r'<smc>(.*?)</smc>', lambda m: sugar_svg(html.unescape(m.group(1)).upper(), 100, 'sm caps'), page, flags=re.S)
    return re.sub(r'<sm>(.*?)</sm>', lambda m: sugar_svg(html.unescape(m.group(1))), page, flags=re.S)


def load(slug):
    src = open(os.path.join(HERE, 'src', 'pages', slug + '.html'), encoding='utf-8').read()
    src = re.sub(r'<!--include:([\w-]+)-->', lambda m: open(os.path.join(HERE, 'src', 'partials', m.group(1) + '.svg'), encoding='utf-8').read(), src)
    meta = json.loads(re.match(r'\s*<!--\s*(\{.*?\})\s*-->', src, re.S).group(1))
    body = re.sub(r'\s*<!--\s*\{.*?\}\s*-->\s*', '', src, count=1, flags=re.S)
    return meta, body, SECTION_RE.findall(body)


def nav(current, sections_by_slug):
    out = []
    for slug, label in PAGES:
        if slug == 'index':
            continue
        here = slug == current
        subs = ''.join(f'<li><a href="{href(slug)}#{sid}" data-spy="{sid}">{lab}</a></li>' for sid, lab in sections_by_slug[slug])
        out.append(f'<li class="nav-page{" is-current" if here else ""}">'
                   f'<a href="{href(slug)}"{" aria-current=page" if here else ""}>{label}</a>'
                   f'<ul class="nav-subs">{subs}</ul></li>')
    return '\n'.join(out)


def prevnext(i):
    links = []
    if i > 0:
        s, l = PAGES[i - 1]
        links.append(f'<a class="pn prev" href="{href(s)}"><span class="label">Previous</span><span class="pn-title">{sugar_svg(l.upper(), 100)}</span></a>')
    else:
        links.append('<span></span>')
    if i < len(PAGES) - 1:
        s, l = PAGES[i + 1]
        links.append(f'<a class="pn next" href="{href(s)}"><span class="label">Next</span><span class="pn-title">{sugar_svg(l.upper(), 100)}</span></a>')
    return ''.join(links)


def main():
    layout = open(os.path.join(HERE, 'src', 'layout.html'), encoding='utf-8').read()
    loaded = {slug: load(slug) for slug, _ in PAGES}
    sections = {slug: v[2] for slug, v in loaded.items()}
    for i, (slug, label) in enumerate(PAGES):
        meta, body, _ = loaded[slug]
        page = (layout
                .replace('{{doc_title}}', ('ICONIC Brand Guidelines' if slug == 'index' else f'{meta["title"]} | ICONIC Brand Guidelines'))
                .replace('{{description}}', re.sub(r'<[^>]+>', '', meta['intro'])[:155])
                .replace('{{slug}}', slug)
                .replace('{{nav}}', nav(slug, sections))
                .replace('{{home_current}}', ' aria-current="page"' if slug == 'index' else '')
                .replace('{{title}}', f'<smd>{meta["title"]}</smd>')
                .replace('{{intro}}', meta['intro'])
                .replace('{{content}}', body)
                .replace('{{prevnext}}', prevnext(i)))
        open(os.path.join(ROOT, href(slug)), 'w', encoding='utf-8').write(sugar(page))
        print('built', href(slug), f'({len(sections[slug])} sections)')


if __name__ == '__main__':
    main()
