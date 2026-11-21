"""Central style definitions for the OsdagBridge PDF design report.

Single source of truth for the report's look & feel: colours, fonts, page
geometry, table padding/rules and longtable header/footer repetition.

Why this module exists
----------------------
Before this module the visual constants were scattered across
``report_generator.preamble()`` and each chapter file: every chapter re-typed
its own ``\\setlength{\\tabcolsep}{...}``, colour names were ad-hoc, page
geometry was a single ``margin=1in`` and none of the 49 long tables emitted
``\\endfirsthead``/``\\endhead`` — so a table that crossed a page boundary
continued without its column headings (and one 12 pt row was painted into the
footer band).  Editing any one of those values meant hunting through nine
files, and the copy-pasted variants had already drifted apart.

Now:

* ``latex_style_block()`` is emitted once from ``preamble()``;
* chapters import ``COLORS``/``COLWIDTHS``/``TABLE`` for the values they
  interpolate, and ``note()``/``xtable()`` helpers for the few places that
  need a styled snippet;
* ``apply_longtable_headers()`` is applied by ``generate_report()`` to the
  assembled document, so every long table — the ones written here and any
  added later — repeats its header row and reserves a footer row.
"""
from __future__ import annotations

import re
from typing import Iterable, Sequence

# ═══════════════════════════════════════════════════════════════════════════
# COLOURS
# ═══════════════════════════════════════════════════════════════════════════

# name -> (model, value).  Keep the count small: every colour here is used in
# at least two chapters, otherwise it belongs inline.
COLORS = {
    "osdagGreen": ("HTML", "91B014"),   # house colour: rules, headings, footer
    "passGreen": ("HTML", "1B7F3B"),    # PASS cells
    "failRed": ("HTML", "C00000"),      # FAIL cells / UR > 1.0
    "warnAmber": ("HTML", "B26B00"),    # WARN cells
    "mutedGrey": ("HTML", "555555"),    # "(continued)" notes, small print
    "chartLine": ("HTML", "C00000"),    # UR limit line in the bar charts
}


def latex_color_defs() -> str:
    """``\\definecolor`` lines for every entry in :data:`COLORS`."""
    out = []
    for name, (model, value) in COLORS.items():
        out.append(r"\definecolor{%s}{%s}{%s}" % (name, model, value))
    return "\n".join(out)


def ctext(name: str, text: str) -> str:
    """Wrap *text* in a colour that is defined by this module."""
    return r"\textcolor{%s}{%s}" % (name, text)


def status_color(text: str) -> str:
    """Colour a PASS/WARN/FAIL string consistently across all chapters."""
    key = str(text).strip().upper()
    if key.startswith("FAIL"):
        return ctext("failRed", text)
    if key.startswith("WARN"):
        return ctext("warnAmber", text)
    if key.startswith("PASS"):
        return ctext("passGreen", text)
    return text


# ═══════════════════════════════════════════════════════════════════════════
# FONTS
# ═══════════════════════════════════════════════════════════════════════════

FONTS = {
    "encoding": "T1",
    "family": "lmodern",       # packaged with every TeX distribution
    "body_size": r"\normalsize",
    "table_size": r"\normalsize",
    "note_size": r"\footnotesize",
    "caption_size": r"\small",
    "heading_family": r"\rmfamily",
}


def latex_font_block() -> str:
    return "\n".join([
        r"\usepackage[%s]{fontenc}" % FONTS["encoding"],
        r"\usepackage{%s}" % FONTS["family"],
        r"\renewcommand{\familydefault}{\rmdefault}",
    ])


# ═══════════════════════════════════════════════════════════════════════════
# PAGE GEOMETRY
# ═══════════════════════════════════════════════════════════════════════════

# The old geometry was ``margin=1in`` with default head/foot skips.  The text
# block then ended ~6 pt below the fancyhdr footer baseline, so a long table
# whose last row did not fit was still shipped and its first column ("G4" on
# p. 28 of the reference report) was printed on top of the running footer.
# A slightly narrower text block plus an explicit footskip keeps every frame
# clear of the footer band.
MARGINS = {
    "top": "2.1cm",
    "bottom": "2.7cm",
    "left": "2.0cm",
    "right": "2.0cm",
    "headheight": "18pt",
    "headsep": "12pt",
    "footskip": "24pt",
}


def latex_geometry_block() -> str:
    opts = ", ".join("%s=%s" % (k, v) for k, v in MARGINS.items())
    return r"\usepackage[a4paper, %s]{geometry}" % opts


# ═══════════════════════════════════════════════════════════════════════════
# TABLES
# ═══════════════════════════════════════════════════════════════════════════

TABLE = {
    "tabcolsep": "6pt",          # default cell padding (was 6 pt in the preamble)
    "tabcolsep_compact": "4pt",  # dense numeric tables (chapters 2, 5)
    "tabcolsep_tight": "3pt",    # widest tables (chapter 4 load-case matrix)
    "tabcolsep_narrow": "3.5pt",  # 7-column bill of materials (chapter 8)
    "arraystretch": "1.12",
    "arraystretch_compact": "1.05",
    "rulewidth": "0.5pt",
    "extrarowheight": "0.6pt",
    "LTpre": "4pt",
    "LTpost": "8pt",
    "row_extra": "[6pt]",        # vertical breathing room between rows
}

# Column widths in cm, shared so that every table lines up on the same grid.
COLWIDTHS = {
    "sno": "1.0cm",
    "label": "5.5cm",
    "value": "10.0cm",
    "label_wide": "4.0cm",
    "value_wide": "11.5cm",
    "num": "1.8cm",
    "num_wide": "2.6cm",
}


def latex_table_block() -> str:
    t = TABLE
    return "\n".join([
        r"\setlength{\tabcolsep}{%s}" % t["tabcolsep"],
        r"\renewcommand{\arraystretch}{%s}" % t["arraystretch"],
        r"\setlength{\LTpre}{%s}" % t["LTpre"],
        r"\setlength{\LTpost}{%s}" % t["LTpost"],
        r"\setlength{\arrayrulewidth}{%s}" % t["rulewidth"],
        r"\setlength{\extrarowheight}{%s}" % t["extrarowheight"],
        # setspace's 1.15 stretch is inherited by longtable, where it skews the
        # row-fit calculation by a few points and is one of the reasons a row
        # could be pushed into the footer band.  Keep tables at a fixed,
        # smaller stretch and restore body text afterwards.
        r"\AtBeginEnvironment{longtable}{\setstretch{1.05}}",
        r"\AtEndEnvironment{longtable}{\setstretch{1.15}}",
        # Custom column types (kept here so no chapter can redefine them).
        r"\newcolumntype{L}[1]{>{\raggedright\arraybackslash}p{#1}}",
        r"\newcolumntype{C}[1]{>{\centering\arraybackslash}p{#1}}",
        r"\newcolumntype{R}[1]{>{\raggedleft\arraybackslash}p{#1}}",
    ])


def table_spacing(kind: str = "compact", arraystretch: str | None = None) -> str:
    """LaTeX snippet applying a named spacing preset from :data:`TABLE`.

    Chapters that need tighter-than-default columns call this instead of
    hard-coding ``\\setlength{\\tabcolsep}``, so the value lives in exactly
    one place.  ``kind`` is one of ``default``, ``compact``, ``tight`` or
    ``narrow``.
    """
    key = "tabcolsep" if kind == "default" else f"tabcolsep_{kind}"
    if key not in TABLE:
        raise KeyError(f"unknown table spacing preset: {kind!r}")
    out = "\\setlength{\\tabcolsep}{%s}" % TABLE[key]
    if arraystretch is not None:
        out += "\n\\renewcommand{\\arraystretch}{%s}" % arraystretch
    return out

def note(text: str, size: str | None = None) -> str:
    """A consistent small italic note under a table."""
    return r"\noindent{\%s\itshape %s\par}" % (
        (size or FONTS["note_size"]).lstrip("\\"), text)


def latex_style_block() -> str:
    """Every style definition, ready to be pasted into the preamble."""
    return "\n".join([
        "% ── Report style: single source of truth (styles.py) ──────────────",
        latex_geometry_block(),
        latex_font_block(),
        latex_color_defs(),
        latex_table_block(),
        r"\captionsetup{labelfont=bf, justification=raggedright, "
        r"singlelinecheck=false, format=plain, font=%s}" % FONTS["caption_size"].lstrip("\\"),
        "% ──────────────────────────────────────────────────────────────────",
    ])


# ═══════════════════════════════════════════════════════════════════════════
# LONG TABLE HEADER / FOOTER REPETITION
# ═══════════════════════════════════════════════════════════════════════════

def count_columns(spec: str) -> int:
    """Number of columns in a longtable/tabular preamble such as ``|C{2cm}|L{3cm}|``.

    Handles the custom ``L/C/R{width}`` types used by this report, the plain
    ``lcrpmbX`` types, and skips alignment modifiers (``|``, ``@{...}``,
    ``>{...}``, ``!{...}``).
    """
    s = spec.strip()
    if s.startswith("{") and s.endswith("}"):
        s = s[1:-1]
    n = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c in "| \t\n":
            i += 1
            continue
        if c in "@>!":
            i += 1
            i = _skip_group(s, i)
            continue
        if c in "lcrX":
            n += 1
            i += 1
            continue
        if c in "pPmMbCLR":
            n += 1
            i += 1
            i = _skip_group(s, i)
            continue
        i += 1
    return n


def _skip_group(s: str, i: int) -> int:
    """Advance past one balanced ``{...}`` group starting at (or after) *i*."""
    while i < len(s) and s[i] != "{":
        if s[i] not in " \t\n":
            return i
        i += 1
    depth = 0
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return i


def _fix_caption_row(body: str) -> str:
    """Terminate ``\\caption{...}`` rows with ``\\\\``.

    longtable's ``\\caption`` is a table row: without the trailing ``\\\\`` the
    ``\\hline`` that follows is an orphan ``\\noalign`` and LaTeX recovers by
    typesetting the header as body text ("Misplaced \\noalign" + "Extra
    alignment tab").  Every one of the 46 captioned tables in the reference
    report hit this, which is why their column headings were not in cells.
    """
    out = []
    for line in body.split("\n"):
        st = line.strip()
        if st.startswith(r"\caption") and not st.endswith(r"\\"):
            line = line.rstrip() + r" \\"
        out.append(line)
    return "\n".join(out)


def _split_header(body: str) -> tuple[str, str, str] | None:
    """Return ``(caption, header, rest)`` for a longtable body, or None.

    ``header`` is the block from the first ``\\hline`` through the second one;
    it is what gets repeated on continuation pages.
    """
    lines = body.split("\n")
    # Locate the first \hline.
    first = next((i for i, ln in enumerate(lines) if ln.strip().startswith(r"\hline")), None)
    if first is None:
        return None
    # The header ends at the next \hline after at least one row line.
    second = None
    for i in range(first + 1, len(lines)):
        if lines[i].strip().startswith(r"\hline"):
            second = i
            break
    if second is None or second == first + 1:
        return None
    # A blank line between \begin{longtable} and the caption is a paragraph
    # break, which longtable reports as "Misplaced \noalign".  Strip the
    # surrounding blank lines from each piece.
    caption = "\n".join(lines[:first]).strip("\n")
    header = "\n".join(lines[first:second + 1]).strip("\n")
    rest = "\n".join(lines[second + 1:]).strip("\n")
    return caption, header, rest


def _table_span(text: str, start: int) -> int:
    """Index just past the matching ``\\end{longtable}`` for the one at *start*."""
    marker = r"\end{longtable}"
    return text.index(marker, start) + len(marker)


def apply_longtable_headers(tex: str, *, repeat_note: bool = True) -> str:
    """Add ``\\endfirsthead``/``\\endhead``/``\\endfoot``/``\\endlastfoot`` to every table.

    Idempotent: tables that already declare ``\\endhead`` are left untouched, so
    the function is safe to apply to hand-written LaTeX as well.
    """
    out = []
    pos = 0
    begin = r"\begin{longtable}"
    while True:
        i = tex.find(begin, pos)
        if i < 0:
            out.append(tex[pos:])
            break
        out.append(tex[pos:i])
        end = _table_span(tex, i)
        block = tex[i:end]

        if r"\endhead" in block:
            out.append(block)
            pos = end
            continue

        # Split "capture group: {spec}" off the \begin{longtable}.
        m = re.match(r"\\begin\{longtable\}(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})", block)
        if not m:
            out.append(block)
            pos = end
            continue
        spec = m.group(1)
        ncol = count_columns(spec)
        head_open = len(m.group(0))
        body = block[head_open:]
        body = body[:-len(r"\end{longtable}")]
        body = _fix_caption_row(body)
        parts = _split_header(body)
        if not parts or ncol < 1:
            out.append(block)
            pos = end
            continue

        caption, header, rest = parts
        # Drop a trailing \hline right before \end{longtable}: \endlastfoot
        # supplies the closing rule, otherwise the table ends with a double rule.
        stripped = rest.rstrip()
        if stripped.endswith(r"\hline"):
            rest = stripped[: -len(r"\hline")].rstrip() + "\n"

        cont_head = (r"\multicolumn{" + str(ncol) + r"}{l}{" + FONTS["note_size"]
                     + r"\itshape (continued from previous page)}\\[" + "6pt]")
        cont_foot = (r"\multicolumn{" + str(ncol) + r"}{r}{" + FONTS["note_size"]
                     + r"\itshape continued on next page\ldots}\\[" + "2pt]")

        new = "\n".join([
            begin + spec, caption,
            header,
            r"\endfirsthead",
            cont_head,
            header,
            r"\endhead",
            # The continuation note sits above the closing rule of the foot, not
            # below it: a rule-less last row hangs into the page footer band.
            cont_foot,
            r"\hline",
            r"\endfoot",
            r"\hline",
            r"\endlastfoot",
            rest,
            r"\end{longtable}",
        ])
        out.append(new)
        pos = end
    return "".join(out)


__all__ = [
    "COLORS", "FONTS", "MARGINS", "TABLE", "COLWIDTHS",
    "latex_style_block", "latex_color_defs", "latex_font_block",
    "latex_geometry_block", "latex_table_block",
    "ctext", "status_color", "note",
    "apply_longtable_headers", "count_columns",
]
