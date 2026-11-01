"""Sets text in Sugar Magic as inline SVG outlines (the font has no web licence, so it is never served as a font file).

sugar_svg('Logo', tracking=0) -> '<svg ...><path .../></svg>' sized in em so it follows CSS font-size,
filled with currentColor so it follows CSS color.
"""
import functools, html
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT_PATH = '/Users/hypedesign/Library/Fonts/sugar-magic-serif.medium.ttf'


@functools.lru_cache(maxsize=1)
def _font():
    tt = TTFont(FONT_PATH)
    blob = hb.Blob.from_file_path(FONT_PATH)
    return tt, hb.Font(hb.Face(blob))


def sugar_svg(text, tracking=0, cls='sm'):
    """tracking is in 1/1000 em, as in Illustrator."""
    tt, font = _font()
    upm = tt['head'].unitsPerEm
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {'kern': True, 'liga': True})
    glyphs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    track = tracking / 1000 * upm
    asc, desc = tt['hhea'].ascent, tt['hhea'].descent  # desc is negative
    pen = SVGPathPen(glyphs)
    x = 0
    n = len(buf.glyph_infos)
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        name = order[info.codepoint]
        # flip y: font units are y-up, SVG is y-down; baseline sits at y=asc
        glyphs[name].draw(TransformPen(pen, (1, 0, 0, -1, x + pos.x_offset, asc - pos.y_offset)))
        x += pos.x_advance + (track if i < n - 1 else 0)
    w = x
    if 'caps' in cls:
        # box capitals to cap height so the svg's bottom edge is the baseline and it lines up with neighbouring text
        cap = tt['OS/2'].sCapHeight
        y0, h, valign = asc - cap, cap, 0
    else:
        y0, h, valign = 0, asc - desc, desc
    label = html.escape(text, quote=True)
    return (f'<svg class="{cls}" role="img" aria-label="{label}" viewBox="0 {round(y0)} {round(w)} {round(h)}" '
            f'style="width:{w / upm:.4f}em;height:{h / upm:.4f}em;vertical-align:{valign / upm:.4f}em" xmlns="http://www.w3.org/2000/svg">'
            f'<path fill="currentColor" d="{pen.getCommands()}"/></svg>')
