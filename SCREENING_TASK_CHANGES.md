# OsdagBridge report generator — LaTeX refactor (FOSSEE Winter Internship 2026 screening task)

Task: <https://docs.google.com/document/d/1CkrRTk1bH3JnEhLIM8RMJodouv-yUlIx>  ·  Repository: `Nidhikhare12/OsdagBridge`, branch `dev`

All work is confined to `src/osdagbridge/core/reports/`. No design, structural or
numerical code was touched: the before/after reports are produced by the same
`PlateGirderBridge.design()` run, so every difference between `Report_Before.pdf`
and `Report_After.pdf` is a typesetting/assembly change.

---

## 1. Result at a glance

| Measure | Before | After |
|---|---|---|
| PDF pages | 51 | 55 (54 numbered + title page) |
| LaTeX errors (`^! ` lines in the log) | **139** (138 = caption-row `&` errors in 46 tables, +1 raw Unicode `≤`) | **0** |
| `Misplaced \noalign` / `\omit` / `Extra alignment tab` | 46 × each | 0 |
| Longtables | 49 | 51 |
| Longtables that repeat their header on continuation pages | 4 | **51 (all)** |
| Content painted over the running footer | 1 page (p. 28) | 0 pages (all 55 checked) |
| Overfull `\hbox` / `\vbox` | present | 0 |
| Undefined references | present | 0 |
| Utilisation-ratio charts (task item 4) | none | 4 |
| Material-quantity charts (task item 5) | none | 2 |
| Live-load tables (task item 3) | 1 mixed table, no unit column | 2 tables (vehicle / footway) with a Unit column |
| Style constants | scattered across 6 chapter files + preamble | one module, `styles.py` |
| Passes over `pdflatex` | 2 | 3 |

Verification commands (both reports were compiled from the same design run, with
the `pdflatex` temp directory kept so the log survives):

```bash
grep -c '^! ' Report_After_kept.log            # 0   (Report_Before: 139)
grep -c 'begin{longtable}' Report_After.tex    # 51
grep -c 'endhead'          Report_After.tex    # 51
pdftotext -bbox Report_After.pdf - | ...       # 0 words below the footer baseline
pdfinfo Report_After.pdf | grep Pages          # 55
```

---

## 2. Files altered

```
src/osdagbridge/core/reports/
├── styles.py             NEW   ~16 KB   single source of truth for layout + longtable post-processing
├── charts.py             NEW   ~17 KB   matplotlib/Agg chart builders (UR bars, quantity bars)
├── report_generator.py  MOD   66 lines  preamble collapse, chart+quantity wiring, header pass, 3-pass compile
├── chap5.py             MOD   56 lines  §5.5.1 utilisation-ratio charts
├── chap7.py             MOD  187 lines  Bill of materials / roll-up / quantity charts, styles-driven
├── chap3.py             MOD   35 lines  vehicle vs footway live loads split into two tables with units
├── report_utils.py      MOD   34 lines  LaTeX-safe handling of ≤ ≥ × ÷ − ° µ Ω → …
├── chap2.py             MOD    5 lines  table spacing from styles.TABLE
├── chap4.py             MOD    4 lines  table spacing from styles.TABLE
└── chap8.py             MOD    5 lines  table spacing from styles.TABLE
```

`doc/` holds the two deliverable PDFs (`Report_Before.pdf`, `Report_After.pdf`).

---

## 3. Root causes found

### 3.1 `\caption` inside `longtable` is a table row (the 138-error cluster)

Every captioned longtable in the original produced three errors —
`! Misplaced \noalign.`, `! Misplaced \omit.`, and
`! Extra alignment tab has been changed to \cr.` — one triple per table.

Cause: inside `longtable`, `\caption{...}` is itself a row and must be terminated
by `\\`. When it is not, the `\hline` that follows is an orphan `\noalign`, and
LaTeX recovers by treating the whole header row as body text. The visible symptom
is a table with no column headings in the PDF while the `.tex` looks correct.

Fix (`styles._fix_caption_row`): append `\\` to any `\caption…` line that does not
already end with one, and strip blank lines between `\begin{longtable}` and the
caption. Error count dropped 139 → 2 immediately, and to 0 once the remaining
Unicode character and the missing asset were handled.

### 3.2 Content painted over the footer (task item 2)

On the reference PDF, page 28, the first-column cell text `G4` had `yMax = 808.2 pt`
while the footer rule sits at `802.1 pt` (page height 841.89 pt): the table row was
drawn over the running footer.

Cause: the body text block (default `geometry` 1 in margins) combined with
`setspace`'s `1.15` stretch inherited *inside* the longtable makes LaTeX's
row-fit arithmetic wrong, so the last row is shipped out past the text block.

Fix: explicit `geometry` (top 2.1 cm, bottom 2.7 cm, left/right 2.0 cm,
`headheight 18 pt`, `headsep 12 pt`, `footskip 24 pt`) plus
`\AtBeginEnvironment{longtable}{\setstretch{1.05}}` /
`\AtEndEnvironment{longtable}{\setstretch{1.15}}`, so table body rows are set at
single-ish spacing while prose keeps 1.15. Measured after the fix: **0 words** with
`yMax` beyond the footer baseline on any of the 55 pages.

### 3.3 Unicode in `\texttt`-free text

`! LaTeX Error: Unicode character ≤ (U+2264) not set up for use with LaTeX.`
`report_utils._tex()` now maps ≤ ≥ × ÷ − ° µ/μ Ω → ← ± ≈ ≠ – — and curly quotes
to math-mode or ASCII equivalents **after** the escaping pass, so the inserted
`$`/backslash survive.

### 3.4 Continuation notes in the longtable foot

The injected "(continued on next page…)" row originally followed the foot rule, so
the note hung *below* the table with nothing under it and crowded the running
footer by about one line. It now sits above the foot rule
(`cont_foot` → `\hline` → `\endfoot`), so the note is closed by a rule and the
footer band keeps its own space (verified page by page with `pdftotext -bbox`).

### 3.5 Caption/heading pagination

§5.5.1 and §7.3 are charts-only subsections. With `[H]` floats a heading can be
left alone at the foot of a page and its figures pushed to the next one. Each now
opens with `\clearpage`, so heading + lead-in + both figures of a group stay
together.

---

## 4. `styles.py` — structure

One module, five constant tables, six helpers; every chapter imports from it, so a
font or padding change is a one-line edit.

```python
COLORS   = {osdagGreen 91B014, passGreen 1B7F3B, failRed C00000,
            warnAmber B26B00, mutedGrey 555555, chartLine C00000}
FONTS    = {encoding T1, family lmodern, body_size, table_size,
            note_size \footnotesize, caption_size \small}
MARGINS  = {top 2.1cm, bottom 2.7cm, left 2.0cm, right 2.0cm,
            headheight 18pt, headsep 12pt, footskip 24pt}
TABLE    = {tabcolsep 6pt / compact 4pt / tight 3pt / narrow 3.5pt,
            arraystretch 1.12 / compact 1.05,
            rulewidth 0.5pt, extrarowheight 0.6pt,
            LTpre 4pt, LTpost 8pt, row_extra [6pt]}
COLWIDTHS= {sno 1.0cm, label 5.5cm, value 10.0cm, label_wide 4.0cm,
            value_wide 11.5cm, num 1.8cm, num_wide 2.6cm}
```

Helpers:

* `latex_color_defs()`, `ctext(name, text)`, `status_color(text)` — colour a cell
  by PASS / WARN / FAIL without each chapter re-deriving the rule.
* `latex_font_block()`, `latex_geometry_block()`, `latex_table_block()` — emit the
  preamble lines; `latex_style_block()` concatenates all three and is the single
  string `report_generator.preamble()` injects.
* `table_spacing(kind="compact", arraystretch=None)` — per-chapter table padding
  preset; replaces the hard-coded `\setlength{\tabcolsep}` literals that were
  duplicated in chap2 (×2), chap4, chap5 (×2), chap7 and chap8 (×2).
* `note(text)` — the italic table footnote used under every table.
* `count_columns(spec)` — column count from a colspec string, handling
  `{|C{1.0cm}|L{3.8cm}|…}`, `{lcr}` and `>{…}p{3cm}` forms.
* `apply_longtable_headers(tex, repeat_note=True)` — the automatic post-process:
  for every longtable it splits caption / header / body, fixes the caption row,
  and emits
  `\endfirsthead` + “(continued from previous page)” + header + `\endhead` +
  “continued on next page…” + `\endfoot` + `\endlastfoot`. Idempotent — a second
  run over already-processed TeX is a no-op (verified: `endhead` count 51 → 51).

`report_generator.generate_report()` calls it once, right before writing
`full_tex`, replacing the old comment that claimed header repetition was
“handled per-table in each chapter file” (it was not: 4 of 49 tables).

---

## 5. `charts.py` — charts

matplotlib with the `Agg` backend (no display needed), returning **PNG bytes**.
Every builder returns `None` instead of raising when its slice of the output
dictionary is missing, so a partial design run still produces a report.

| Chart | Data source | Section |
|---|---|---|
| `ur_girders` | `design_results.per_girder.G1…G6.checks[]`, grouped by check id like Table 5.22 | §5.5.1 |
| `ur_deck_slab` | `deck_report_values` (`KEY_DD_*` pairs: sag/hog/overhang/punching/shear) | §5.5.1 |
| `ur_cross_bracing` | `get_cb_pairs()` + `get_cb_efficiency(pair, member, force_type)` | §5.5.1 |
| `ur_end_diaphragm` | same facade, end-diaphragm pairs | §5.5.1 |
| `qty_steel_components` | `<prefix>_wt_total` tonnage, sorted descending | §7.3 |
| `qty_concrete_rebar` | deck concrete volume vs reinforcement weight, independent scales | §7.3 |

Conventions: bars green `< 0.85`, amber `0.85–1.00`, red `> 1.00`; a red dashed
`UR = 1.0` line drawn twice (white halo underneath so it stays visible where it
crosses a failing red bar); value labels outside the bar, but **inside** the bar in
white when the bar ends near the limit, so a label never sits on the limit line;
legend below the axes; DPI 220. The charts are drawn from exactly the numbers
Tables 5.1–5.22 print, so a bar and its table row cannot disagree.

Delivery: the PNG bytes go into `payload.figure_data` *before* the existing figure
write loop, so they land in the same `images/` directory as the CAD drawings and
the chapters receive paths through the usual `fig_paths` dictionary. A chart
failure is logged (`Chapter 5 charts failed: …`) and the report still builds.

`ch5_design_checks()` and `ch7_quantities()` therefore gained one optional
argument, `fig_paths=None`; their existing call sites remain valid.

---

## 6. Task item 3 — vehicle and footway live loads

`chap3.py` had one 2-column table mixing `Vehicles Considered`, `Impact Factor`,
`Braking Load` and `Footpath Live Load`, with no unit column. It is now:

* **Table 3.3 — Vehicle Live Loads (LL), per IRC 6**: Vehicle, Impact Factor,
  Braking Load (`kN`, with the equivalent `t` in the same cell).
* **Table 3.4 — Footway Live Load, per IRC 6**: Footpath pressure mode, Footway
  load (`kN/m²`).

Both carry an explicit **Unit** column, and the paragraph above them states why the
two load families are tabulated separately (different code clause, different
application point, different safety factor).

---

## 7. Task item 5 — material quantities

`ch7.py` was a 33-line function returning one hard-coded 7-column longtable of
`N.A.` strings. It now builds three sections from `styles` constants:

* **§7.1 Bill of Materials** — 7 columns, one row per component, quoting the
  arithmetic per unit (`0.03492 m² × 30.00 m = 1.04756 m³`), number of units, total
  volume, weight per unit, total weight.
* **§7.2 Quantity Roll-up** — girders/bracing/studs, crash barrier, all steel,
  deck concrete, reinforcement, reinforcement content per m³, reinforcement share
  of all ferrous material.
* **§7.3 Quantity Charts** — the two charts above.

The roll-up is arithmetically closed: `32.89 + 45.34 = 78.86 MT` of steel,
`7.56 × 1000 / 63.00 = 120.0 kg/m³`, `7.56 / 86.42 = 8.7 %`.

---

## 8. Compile passes

`pdflatex` now runs **three** times. With the TOC, the repeated longtable headers
and `\pageref{LastPage}`, two passes can leave the footer total one page behind the
real page count. The third pass is cheap (≈15 s on this document) and makes the
“Page x of y” line correct on the first read of the output. The numbered pages
(`1…54`) plus the title page account for the 55 PDF pages.

---

## 9. Reproducing

```bash
# environment (the design pipeline needs the osdag conda packages)
conda create -y -p ./obc -c osdag -c geompy -c conda-forge python=3.11 osdag
conda run -p ./obc python -m pip install --no-deps -e .
conda run -p ./obc python -m pip install scipy fiona shapely pydantic matplotlib \
        openseespy opsvis xarray

# report (30 m span, 7.5 m carriageway defaults from the frontend)
cd src && python -m osdagbridge.desktop      # GUI path, unchanged
# or headless, as used for the two deliverable PDFs:
python drive/make_report.py Report_After
```

The headless driver is shipped with this submission (`make_report.py`,
`ob_driver.py`, `keep_run.py`); it only calls the public API —
`PlateGirderBridge.set_input()`, `.design()`, `.generate_design_report()` — so the
report under test is exactly the one the GUI produces.

The two deliverables come from two different trees and must be regenerated separately:
`Report_After.pdf` from `report-latex-refactor`, and `Report_Before.pdf` from `dev`
(d74f56d). Running the driver on the refactor branch with the stem `Report_Before`
silently produces a ~55-page refactored render, not the 51-page baseline.

---

## 10. Known limitations

* Figures are written to the `pdflatex` temp directory and referenced there by
  absolute path (pre-existing behaviour). The `.tex` alone is not self-contained;
  compiling it needs the sibling `images/` directory.
* In the headless run the report looks for the Osdag logo at `assets/osdag_logo.png`
  relative to the temp dir; the GUI path copies it in. If the asset is missing the
  logo block is skipped (a warning, not an error).
* Chart reading of the output dictionary is defensive: unknown keys yield `None`
  and the chapter silently omits that figure rather than printing an empty axes.
* The default 30 m / 7.5 m design fails the total-load deflection check
  (51.137 mm vs L/600 = 50.0 mm on all four girders) — that is what the design code
  computes for the defaults, and the report reports it honestly (`FAIL` in
  Table 5.9 and the red bar in Figure 5.1).
* The default design fails more than the deflection check. The driver run behind
  `Report_After.pdf` ends with overall status `FAIL`
  (`PASS / WARN / FAIL: 13 / 0 / 1`) and marks at least two further rows `*FAIL*`:
  fatigue normal stress (145.45 vs 92.49, ratio 1.573) and intermediate-stiffener
  leg ≤ H_limit (250.00 vs 169.03, ratio 1.479). The generator renders those rows
  faithfully, which is the point of the task: the report is a reporting layer, and
  fixing the underlying design is out of scope. The full console log is shipped as
  `driver_run.log`.
* Load-combination table row order follows dictionary iteration order and is not
  stable between renders. The row set is identical every time (48 rows:
  `BASIC_1..6`, `SLS_FREQUENT_1`, `SLS_QP_1..2`, `SLS_RARE_1..6`, `ULS`), as are the
  page count (55) and every check result, but the sequence of those rows can differ,
  so two renders of `Report_After.pdf` are not byte-identical (879,044 B vs 879,000 B
  observed between two runs of the same code). Pinning the order means sorting the
  combination names in `chap3.py`/`chap5.py` before table emission.
