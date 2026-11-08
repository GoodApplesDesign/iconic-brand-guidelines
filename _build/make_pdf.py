"""Builds the PDF version of the guidelines: _build/src/print.html + print.css -> assets/downloads/ICONIC-Brand-Guidelines.pdf

A4 landscape, on the grid of the Identity Evolution deck (Logo Development-v3.ai): Noir pages, a Sugar Magic label top
left, copy on the left and visuals on the right, a thin gold rule and a two-part footer. Chrome prints it, so logos,
diagrams and type stay vector, and Sugar Magic is outlined as on the site (never embedded as a font).

Run from anywhere:  python3 _build/make_pdf.py   (needs Google Chrome, plus what build.py needs)

Page source conventions (on top of build.py's <smd>, <smc>, <sm> and <!--include:name-->)
- <article class="page" data-section="Logo" data-label="Logo suite" data-toc="Logo suite"> is one page.
  data-section names the footer, data-label the top-left label, and data-toc lists the page in the contents.
- class="page bare" pages (the covers) get no label or footer.
- {{toc}} becomes the contents, {{site}} the live site's address and {{site_short}} the same without https://.
"""
import html, os, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from build import sugar  # noqa: E402

SITE = 'https://goodapplesdesign.github.io/iconic-brand-guidelines/'
CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
OUT = os.path.join(ROOT, 'assets', 'downloads', 'ICONIC-Brand-Guidelines.pdf')
PAGE_RE = re.compile(r'<article\b([^>]*)>(.*?)</article>', re.S)
COLUMNS = [['Logo'], ['Colour'], ['Typography', 'Downloads']]  # contents columns


def attr(attrs, name):
    m = re.search(rf'\b{name}="([^"]*)"', attrs)
    return m.group(1) if m else ''


def contents(pages):
    """A column per section (Typography shares its column with Downloads), every entry linked to its page."""
    secs = {}
    for no, (attrs, _) in enumerate(pages, 1):
        sec, toc = attr(attrs, 'data-section'), attr(attrs, 'data-toc')
        if sec and sec != 'Foundations':
            s = secs.setdefault(sec, {'first': no, 'items': []})
            if toc and toc != sec:
                s['items'].append((toc, no))

    def block(name):
        s = secs[name]
        items = ''.join(f'<li><a href="#p{no}"><span>{html.escape(t)}</span><span class="n">{no:02d}</span></a></li>'
                        for t, no in s['items'])
        return (f'<div class="toc-sec"><a class="toc-h" href="#p{s["first"]}"><smc>{name}</smc>'
                f'<span class="n">{s["first"]:02d}</span></a>{f"<ul>{items}</ul>" if items else ""}</div>')
    return '<div class="toc">' + ''.join('<div>' + ''.join(block(n) for n in col if n in secs) + '</div>'
                                         for col in COLUMNS) + '</div>'


def frame(no, attrs, body):
    """Adds the page's id, its top-left label and its footer (rule, title, section and page number)."""
    if 'bare' in attr(attrs, 'class').split():
        return f'<article id="p{no}"{attrs}>{body}</article>'
    return (f'<article id="p{no}"{attrs}><header class="pl"><smc>{attr(attrs, "data-label")}</smc></header>'
            f'<div class="body">{body}</div>'
            f'<footer class="foot"><span class="l"><smc>ICONIC Beverages brand guidelines</smc></span>'
            f'<span class="r"><smc>{attr(attrs, "data-section")}</smc><span class="no">{no:02d}</span></span></footer></article>')


def font_faces(tmp):
    """Aileron from its OTFs (Chrome embeds them as proper fonts, where the site's WOFF2s become Type 3)."""
    faces = []
    with zipfile.ZipFile(os.path.join(ROOT, 'assets', 'downloads', 'Aileron.zip')) as z:
        for name, weight, style in [('Light', 300, 'normal'), ('LightItalic', 300, 'italic'), ('Regular', 400, 'normal'),
                                    ('SemiBold', 600, 'normal'), ('Bold', 700, 'normal')]:
            path = os.path.join(tmp, f'Aileron-{name}.otf')
            open(path, 'wb').write(z.read(f'Aileron/Aileron-{name}.otf'))
            faces.append(f'@font-face {{ font-family: Aileron; src: url("{Path(path).as_uri()}") format("opentype"); '
                         f'font-weight: {weight}; font-style: {style}; }}')
    return '\n'.join(faces)


def main():
    src = open(os.path.join(HERE, 'src', 'print.html'), encoding='utf-8').read()
    src = re.sub(r'<!--include:([\w-]+)-->', lambda m: open(os.path.join(HERE, 'src', 'partials', m.group(1) + '.svg'),
                                                           encoding='utf-8').read(), src)
    src = re.sub(r'<!--.*?-->', '', src, flags=re.S)
    pages = PAGE_RE.findall(src)
    body = '\n'.join(frame(no, attrs, content) for no, (attrs, content) in enumerate(pages, 1))
    body = (body.replace('{{toc}}', contents(pages)).replace('{{site}}', SITE)
            .replace('{{site_short}}', SITE.replace('https://', '').rstrip('/')))
    tokens = re.search(r':root \{.*?\n\}', open(os.path.join(ROOT, 'assets', 'css', 'site.css'), encoding='utf-8').read(), re.S).group(0)
    css = open(os.path.join(HERE, 'src', 'print.css'), encoding='utf-8').read()

    with tempfile.TemporaryDirectory() as tmp:
        doc = (f'<!doctype html><html lang="en-AU"><head><meta charset="utf-8"><base href="{Path(ROOT).as_uri()}/">'
               f'<title>ICONIC Beverages brand guidelines</title><style>{font_faces(tmp)}\n{tokens}\n{css}</style></head>'
               f'<body>{body}</body></html>')
        page = os.path.join(tmp, 'guidelines.html')
        open(page, 'w', encoding='utf-8').write(sugar(doc))
        for attempt in range(3):  # headless Chrome now and then exits early; a retry always works
            if os.path.exists(OUT):
                os.remove(OUT)
            r = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--allow-file-access-from-files', '--no-pdf-header-footer',
                                '--run-all-compositor-stages-before-draw', '--virtual-time-budget=15000',
                                f'--print-to-pdf={OUT}', Path(page).as_uri()], capture_output=True)
            if r.returncode == 0 and os.path.exists(OUT):
                break
        else:
            raise RuntimeError('Chrome could not print the PDF')
    print('wrote', os.path.relpath(OUT, ROOT), f'({len(pages)} pages, {os.path.getsize(OUT) // 1024} KB)')


if __name__ == '__main__':
    main()
