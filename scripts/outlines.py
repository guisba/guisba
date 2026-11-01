"""Archivo text as SVG outlines, shared by the README build and the activity cards."""
from pathlib import Path
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

FONT = hb.Font(hb.Face(hb.Blob.from_file_path(str(Path(__file__).with_name("fonts") / "Archivo.ttf"))))
UPEM = FONT.face.upem


def shape(text, size, wght=400, wdth=100):
    FONT.set_variations({"wght": wght, "wdth": wdth})
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(FONT, buf, {"kern": True, "liga": True})
    return buf, size / UPEM


def measure(text, size, **kw):
    buf, s = shape(text, size, **kw)
    return sum(p.x_advance for p in buf.glyph_positions) * s


def text_path(text, x, y, size, fill, wght=400, wdth=100, anchor="start", cls=None, track=0.0):
    """SVG <path> drawing `text` with its baseline at y. track is em-relative letter spacing."""
    buf, s = shape(text, size, wght, wdth)
    total = sum(p.x_advance for p in buf.glyph_positions) * s + track * size * (len(buf.glyph_infos) - 1)
    if anchor == "end":
        x -= total
    elif anchor == "middle":
        x -= total / 2
    pen = SVGPathPen(None, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    cx = x
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        tp = TransformPen(pen, (s, 0, 0, -s, cx + pos.x_offset * s, y - pos.y_offset * s))
        FONT.draw_glyph_with_pen(info.codepoint, tp)
        cx += pos.x_advance * s + track * size
    c = f' class="{cls}"' if cls else ""
    return f'<path{c} fill="{fill}" d="{pen.getCommands()}"/>'


def wrap(text, size, width, **kw):
    lines, cur = [], ""
    for w in text.split():
        nxt = f"{cur} {w}".strip()
        if cur and measure(nxt, size, **kw) > width:
            lines.append(cur)
            cur = w
        else:
            cur = nxt
    return lines + [cur]


def fit(text, width, **kw):
    return width / measure(text, 100, **kw) * 100
