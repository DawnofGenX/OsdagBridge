"""Figure generation for the OsdagBridge design report.

Every chart in the report is drawn here, with matplotlib's Agg backend, so the
report assembles identically on machines without a display and the visual
language (palette, UR limit line, annotation style) stays consistent with
:mod:`osdagbridge.core.reports.styles`.

Two families are produced:

* **Utilisation-ratio panels** for Chapter 5 -- steel plate girders, concrete
  deck slab, cross bracing and end diaphragms.  Each bar is ``UR = demand /
  capacity`` for one check; the dashed red line is ``UR = 1.0``.
* **Quantity panels** for Chapter 7 -- steel tonnage by component and the
  concrete-volume / reinforcement-weight pair.

Charts return PNG bytes; ``generate_report()`` drops them into ``images/`` in
the pdflatex working directory and hands the resulting paths to the chapters.
Nothing here raises: a missing or unusable data series returns ``None`` and
the calling chapter simply omits that figure, so a partially populated
``output_dict`` can never break PDF generation.
"""
from __future__ import annotations

import io
from typing import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402  (must follow matplotlib.use)
from matplotlib.ticker import MaxNLocator  # noqa: E402

from .styles import COLORS  # noqa: E402

# ═══════════════════════════════════════════════════════════════════════════
# PALETTE / GLOBAL LOOK
# ═══════════════════════════════════════════════════════════════════════════


def _hex(name: str) -> str:
    model, value = COLORS[name]
    return "#" + value


GREEN = _hex("passGreen")
AMBER = _hex("warnAmber")
RED = _hex("failRed")
GREY = _hex("mutedGrey")
HOUSE = _hex("osdagGreen")
LIMIT = _hex("chartLine")

DPI = 220
FIGSIZE = (7.4, 3.5)


def _style_axes(ax, title: str, subtitle: str = "") -> None:
    """Left-aligned title with the subtitle on its own band underneath.

    The subtitle is drawn in axes coordinates above the title's padding so the
    two never collide (a 10 pt title pad with the subtitle at 1.02 overlapped
    on every panel).
    """
    ax.set_title(title, fontsize=10.5, fontweight="bold", loc="left", pad=24)
    if subtitle:
        ax.text(
            0.0, 1.015, subtitle, transform=ax.transAxes,
            fontsize=7.6, color="#555555", va="bottom", ha="left",
        )
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#BBBBBB")
    ax.tick_params(colors="#333333", labelsize=8)
    ax.grid(axis="x", color="#E4E4E4", linewidth=0.7)
    ax.set_axisbelow(True)


def _color_for(ur: float) -> str:
    if ur > 1.0:
        return RED
    if ur >= 0.85:
        return AMBER
    return GREEN


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=DPI, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


# ═══════════════════════════════════════════════════════════════════════════
# UTILISATION RATIO PANELS
# ═══════════════════════════════════════════════════════════════════════════


def ur_bar_chart(
    labels: Sequence[str],
    urs: Sequence[float],
    title: str,
    subtitle: str = "",
    note: str = "Bars show UR = demand / capacity; the dashed line is the UR = 1.0 limit.",
) -> bytes | None:
    """Horizontal UR bars with a ``UR = 1.0`` limit line and value labels."""
    rows = [(str(l), float(u)) for l, u in zip(labels, urs) if u is not None]
    rows = [(l, u) for l, u in rows if u == u]  # drop NaN
    if not rows:
        return None

    labels = [r[0] for r in rows]
    urs = [r[1] for r in rows]
    ypos = list(range(len(rows)))

    fig, ax = plt.subplots(figsize=FIGSIZE)
    bars = ax.barh(
        ypos, urs, height=0.62,
        color=[_color_for(u) for u in urs],
        edgecolor="white", linewidth=0.6, zorder=3,
    )
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()  # first check at the top

    top = max(max(urs), 1.0)
    ax.set_xlim(0, max(top * 1.18, 1.05))
    # White halo underneath keeps the red limit line visible where it crosses a
    # red (failing) bar; the label runs along the line so it never sits on a bar.
    ax.axvline(1.0, color="white", linewidth=3.6, zorder=4, alpha=0.95)
    ax.axvline(1.0, color=LIMIT, linestyle=(0, (4, 3)), linewidth=1.2, zorder=5)
    ax.text(
        1.0 - 0.012, 0.985, "UR = 1.0", color=LIMIT, fontsize=7.2,
        ha="right", va="top", fontweight="bold", rotation=90,
        transform=ax.get_xaxis_transform(), zorder=6,
    )
    for bar, ur in zip(bars, urs):
        # A label printed outside a long bar would run through the dashed
        # UR = 1.0 line, so a near-limit bar carries its value inside the bar
        # in white instead, where it stays legible.
        if ur > 0.88:
            ax.text(
                bar.get_width() - top * 0.015,
                bar.get_y() + bar.get_height() / 2.0,
                f"{ur:.2f}", va="center", ha="right", fontsize=7.8,
                color="white", fontweight="bold", zorder=7,
            )
        else:
            ax.text(
                bar.get_width() + top * 0.015,
                bar.get_y() + bar.get_height() / 2.0,
                f"{ur:.2f}", va="center", ha="left", fontsize=7.8, color="#222222",
            )
    ax.xaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.set_xlabel("Utilisation ratio (UR)", fontsize=8, color="#333333")
    _style_axes(ax, title, subtitle)
    fig.text(0.0, -0.10, note, fontsize=7, color=GREY, ha="left")

    # Colour key: green / amber / red bands of the same encoding as the bars.
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=GREEN),
        plt.Rectangle((0, 0), 1, 1, color=AMBER),
        plt.Rectangle((0, 0), 1, 1, color=RED),
    ]
    ax.legend(
        handles, ["< 0.85 (pass)", "0.85 – 1.00 (near limit)", "> 1.00 (fail)"],
        loc="upper left", fontsize=7, frameon=False, ncol=3,
        bbox_to_anchor=(0.0, -0.13), borderaxespad=0.0, handlelength=1.1,
        handleheight=0.7, columnspacing=1.4,
    )
    return _png(fig)


def _safe_float(value) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None


def _girder_rows(bridge) -> list[tuple[str, str, float]]:
    """(label, group, ur) for the girder checks, worst girder per check.

    Mirrors the Table 5.22 selection: skip edge-beam keys (``EB*``) and take
    the highest DCR across girders for each check id.
    """
    per_girder = (bridge.output_dict.get("design_results", {}) or {}).get("per_girder", {}) or {}
    wanted = [
        ("ULS flexure", {1}),
        ("ULS shear", {2}),
        ("LTB (construction)", {5}),
        ("Deflection", {13, 14}),
        ("Stress limitation", {11}),
        ("Fatigue", {8, 9}),
    ]
    out = []
    for label, ids in wanted:
        best = None
        for g, gd in per_girder.items():
            if str(g).startswith("EB"):
                continue
            for chk in (gd.get("checks") or []):
                if chk.get("check_id") in ids:
                    d = _safe_float(chk.get("dcr"))
                    if d is not None and (best is None or d > best):
                        best = d
        if best is not None:
            out.append((label, "Plate girder", best))
    return out


def _deck_rows(bridge) -> list[tuple[str, str, float]]:
    deck = bridge.output_dict.get("deck_report_values", {}) or {}
    if not deck:
        return []
    pairs = [
        ("Flexure (sagging)", "deck.report.m_uls_sag", "deck.report.mu_bot"),
        ("Flexure (hogging)", "deck.report.m_uls_hog", "deck.report.mu_top"),
        ("Cantilever overhang", "deck.report.m_uls_oh", "deck.report.mu_oh"),
        ("Punching shear", "deck.report.punch_ved", "deck.report.vrd_c_mpa"),
        ("One-way shear", "deck.report.shear_ved", "deck.report.shear_vrdc"),
    ]
    out = []
    for label, dk, ck in pairs:
        dem = _safe_float(deck.get(dk))
        cap = _safe_float(deck.get(ck))
        if dem is None or cap is None or cap <= 0:
            continue
        out.append((label, "Deck slab", dem / cap))
    return out


def _transverse_rows(bridge, force_type: str, group: str) -> list[tuple[str, str, float]]:
    """Worst UR per panel for one transverse-member force type."""
    try:
        pairs = bridge.get_cb_pairs() or []
    except Exception:  # pragma: no cover - defensive: helper may not exist
        return []
    out = []
    for pair in pairs:
        worst = None
        for member in ("diagonal", "chord"):
            try:
                ur = _safe_float(bridge.get_cb_efficiency(pair, member, force_type))
            except Exception:
                ur = None
            if ur is not None and (worst is None or ur > worst):
                worst = ur
        if worst is not None:
            out.append((f"{pair} ({force_type})", group, worst))
    return out


def _end_diaphragm_is_bracing(bridge) -> bool:
    for key, value in bridge.input_dict.items():
        if str(key).startswith("member_properties.end_diaphragm_details.type") and value:
            return "brac" in str(value).strip().lower()
    return False


def chapter5_charts(bridge) -> dict[str, bytes]:
    """UR panels for §5.5, keyed by the figure names used in the LaTeX."""
    charts: dict[str, bytes] = {}

    girder = _girder_rows(bridge)
    if girder:
        lbl = [r[0] for r in girder]
        ur = [r[2] for r in girder]
        png = ur_bar_chart(
            lbl, ur,
            "Steel plate girders — utilisation ratio by check",
            "Worst girder of the deck; demand from the governing load combination.",
        )
        if png:
            charts["ur_girders"] = png

    deck = _deck_rows(bridge)
    if deck:
        png = ur_bar_chart(
            [r[0] for r in deck], [r[2] for r in deck],
            "Concrete deck slab — utilisation ratio by check",
            "Deck designed for the IRC:6 basic ULS combination.",
        )
        if png:
            charts["ur_deck_slab"] = png

    cb = _transverse_rows(bridge, "compression", "Cross bracing") + \
        _transverse_rows(bridge, "tension", "Cross bracing")
    if cb:
        png = ur_bar_chart(
            [r[0] for r in cb], [r[2] for r in cb],
            "Cross bracing — utilisation ratio per panel",
            "Worst member (diagonal or chord) of each panel, compression and tension.",
        )
        if png:
            charts["ur_cross_bracing"] = png

    if _end_diaphragm_is_bracing(bridge):
        ed = _transverse_rows(bridge, "compression", "End diaphragm") + \
            _transverse_rows(bridge, "tension", "End diaphragm")
        if ed:
            png = ur_bar_chart(
                [r[0] for r in ed], [r[2] for r in ed],
                "End diaphragms — utilisation ratio per panel",
                "Configured as cross bracing: axial design, compression and tension.",
            )
            if png:
                charts["ur_end_diaphragm"] = png

    return charts


# ═══════════════════════════════════════════════════════════════════════════
# CHAPTER 7 — QUANTITIES
# ═══════════════════════════════════════════════════════════════════════════

# (report label, input key prefix)
_STEEL_COMPONENTS = [
    ("Girders", "steel_girders"),
    ("Bracing — top chord", "bracing_top"),
    ("Bracing — bottom chord", "bracing_bot"),
    ("Bracing — diagonal", "bracing_diag"),
    ("Shear studs", "shear_studs"),
    ("Crash barrier", "crash_barrier"),
]


def _qty(inputs, prefix: str, suffix: str) -> float:
    raw = inputs.get(f"{prefix}_{suffix}")
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw or "").strip()
    for token in text.replace(",", " ").split():
        try:
            return float(token)
        except ValueError:
            continue
    return 0.0


def steel_tonnage_chart(inputs) -> bytes | None:
    """Steel mass by component, in tonnes."""
    rows = []
    for label, prefix in _STEEL_COMPONENTS:
        mt = _qty(inputs, prefix, "wt_total")
        if mt > 0:
            rows.append((label, mt))
    if not rows:
        return None

    # Largest component on top: a take-off is read as a ranking, so the rows
    # are sorted by mass instead of by the order the keys happen to sit in.
    rows.sort(key=lambda r: r[1], reverse=True)
    maxv = max(r[1] for r in rows)
    total = sum(r[1] for r in rows)

    fig, ax = plt.subplots(figsize=FIGSIZE)
    ypos = list(range(len(rows)))
    bars = ax.barh(ypos, [r[1] for r in rows], height=0.62,
                   color=HOUSE, edgecolor="white", linewidth=0.6, zorder=3)
    ax.set_yticks(ypos)
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(0, maxv * 1.22)

    # Components worth < 2 % of the governing mass cannot be drawn to scale
    # (bracing and studs are two orders of magnitude below the girders), so
    # they get a marker at the axis instead of an invisible bar - the label
    # still carries the exact number.
    tiny = 0.02 * maxv
    for bar, (_, value) in zip(bars, rows):
        x = bar.get_width()
        if value < tiny:
            ax.plot([0.0], [bar.get_y() + bar.get_height() / 2.0], marker="<",
                    markersize=3.4, color=HOUSE, zorder=4, clip_on=False)
            x = maxv * 0.012
        ax.text(x + maxv * 0.015, bar.get_y() + bar.get_height() / 2.0,
                f"{value:.2f} t", va="center", ha="left", fontsize=7.8, color="#222222")
    ax.set_xlabel("Mass (tonnes)", fontsize=8, color="#333333")
    _style_axes(ax, "Structural steel — mass by component",
                f"Total steel take-off: {total:.2f} t (excluding reinforcement).")
    return _png(fig)


def concrete_rebar_chart(inputs) -> bytes | None:
    """Concrete volume (m³) beside reinforcement mass (t)."""
    vol = _qty(inputs, "concrete_deck", "vol_total")
    rebar_t = _qty(inputs, "rebar_deck", "wt_total")
    if vol <= 0 and rebar_t <= 0:
        return None

    fig, axes = plt.subplots(1, 2, figsize=FIGSIZE)
    pairs = [
        (axes[0], "Deck concrete volume", vol, "m³", HOUSE),
        (axes[1], "Deck reinforcement", rebar_t, "t", AMBER),
    ]
    for ax, title, value, unit, colour in pairs:
        ax.bar([0], [value], width=0.42, color=colour,
               edgecolor="white", linewidth=0.6, zorder=3)
        ax.set_xticks([0])
        ax.set_xticklabels([title], fontsize=8.5)
        ax.set_xlim(-0.7, 0.7)
        ax.set_ylim(0, max(value * 1.25, 1.0))
        ax.text(0, value + max(value * 1.25, 1.0) * 0.03,
                f"{value:.2f} {unit}", ha="center", va="bottom",
                fontsize=9, fontweight="bold", color="#222222")
        ax.grid(axis="y", color="#E4E4E4", linewidth=0.7)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#BBBBBB")
        ax.tick_params(colors="#333333", labelsize=8)

    if vol > 0:
        fig.suptitle(
            f"Concrete and reinforcement — {rebar_t / vol * 1000:.0f} kg of steel per m³ of concrete",
            fontsize=9.4, color="#333333", x=0.02, ha="left",
        )
    return _png(fig)


def chapter7_charts(inputs) -> dict[str, bytes]:
    """Quantity panels for Chapter 7, keyed by the figure names used in LaTeX."""
    charts: dict[str, bytes] = {}
    png = steel_tonnage_chart(inputs)
    if png:
        charts["qty_steel_components"] = png
    png = concrete_rebar_chart(inputs)
    if png:
        charts["qty_concrete_rebar"] = png
    return charts
