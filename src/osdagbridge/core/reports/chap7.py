"""Chapter 7 — Material take-off and quantity summary.

The table values come from
:func:`osdagbridge.core.boq.boq_generator.calculate_material_quantities`, which
``generate_report()`` merges into ``payload.inputs`` before assembly.  All
styling (column widths, rule weights, cell padding) is imported from
``styles.py`` so this chapter can never drift from the rest of the report.
"""

from .styles import COLWIDTHS, TABLE, note

# (serial, description, quantity-key prefix, unit)
_ITEMS = [
    ("1",    "Structural Steel (IS 2062) for Girders", "steel_girders",  "m$^3$"),
    ("2(a)", "Cross Bracing --- Top Chord",            "bracing_top",    "m$^3$"),
    ("2(b)", "Cross Bracing --- Bottom Chord",         "bracing_bot",    "m$^3$"),
    ("2(c)", "Cross Bracing --- Diagonal",             "bracing_diag",   "m$^3$"),
    ("3",    "Concrete (M40) for Deck Slab",           "concrete_deck",  "m$^3$"),
    ("4",    "Reinforcement Steel (Fe 500)",           "rebar_deck",     "m$^3$"),
    ("5",    "Shear Stud Connectors",                  "shear_studs",    "m$^3$"),
    ("6",    "Crash Barrier",                          "crash_barrier",  "m$^3$"),
]

# Which prefixes roll up into which total (Chapter 7.2)
_STEEL_ITEMS = ("steel_girders", "bracing_top", "bracing_bot", "bracing_diag", "shear_studs")
_CONCRETE_ITEMS = ("concrete_deck",)
_REBAR_ITEMS = ("rebar_deck",)


def _cell(value):
    """Return a LaTeX-safe cell string (``N.A.`` for missing values)."""
    if value is None:
        return "N.A."
    text = str(value).strip()
    return text if text else "N.A."


def _as_float(value):
    """Parse a quantity cell into ``float``; ``None`` when it is not a number."""
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _sum(input_dict, prefixes, suffix):
    """Sum ``<prefix>_<suffix>`` across prefixes, ignoring ``N.A.`` cells."""
    total = 0.0
    for prefix in prefixes:
        value = _as_float(input_dict.get(f"{prefix}_{suffix}"))
        if value:
            total += value
    return total


def ch7_quantities(input_dict, fig_paths=None):
    """Return Chapter 7 as a LaTeX fragment.

    Parameters
    ----------
    input_dict : dict
        Design inputs, already merged with the ``calculate_material_quantities``
        results.
    fig_paths : dict, optional
        Figure name -> path written by ``generate_report()``.  The two quantity
        charts (``qty_steel_components``, ``qty_concrete_rebar``) are drawn in
        ``charts.py``; when they are absent the chapter simply omits them.
    """
    input_dict = input_dict or {}

    rows = []
    for serial, description, prefix, unit in _ITEMS:
        rows.append(
            "{} & {} & {} & {} & {} & {} & {} \\\\".format(
                serial,
                description,
                _cell(input_dict.get(prefix + "_vol_formula")),
                _cell(input_dict.get(prefix + "_qty")),
                _cell(input_dict.get(prefix + "_vol_total")),
                _cell(input_dict.get(prefix + "_wt_single")),
                _cell(input_dict.get(prefix + "_wt_total")),
            )
        )

    # ── Roll-up totals (7.2) ────────────────────────────────────────────────
    steel_total = _sum(input_dict, _STEEL_ITEMS, "wt_total")
    concrete_total = _sum(input_dict, _CONCRETE_ITEMS, "vol_total")
    rebar_total = _sum(input_dict, _REBAR_ITEMS, "wt_total")

    def _fmt(value, unit=""):
        return "{:.2f}{}".format(value, unit) if value else "N.A."

    barrier_total = _sum(input_dict, ("crash_barrier",), "wt_total")
    ferrous_total = steel_total + barrier_total + rebar_total

    rollup_rows = [
        "Steel --- girders, bracing, shear studs & {} & MT \\\\".format(_fmt(steel_total)),
        "Steel --- crash barrier & {} & MT \\\\".format(_fmt(barrier_total)),
        "Steel --- all items & {} & MT \\\\".format(_fmt(steel_total + barrier_total)),
        "Concrete (deck slab) & {} & m$^3$ \\\\".format(_fmt(concrete_total)),
        "Reinforcement steel & {} & MT \\\\".format(_fmt(rebar_total)),
        "Reinforcement content per m$^3$ of concrete & {} & kg/m$^3$ \\\\".format(
            "{:.1f}".format(rebar_total * 1000.0 / concrete_total) if concrete_total else "N.A."
        ),
        "Reinforcement share of all ferrous material & {} & \\% \\\\".format(
            "{:.1f}".format(100.0 * rebar_total / ferrous_total) if ferrous_total else "N.A."
        ),
    ]

    # ── Charts ──────────────────────────────────────────────────────────────
    figures = []
    for key, caption, label in [
        ("qty_steel_components", "Steel tonnage by component", "fig:qty-steel"),
        ("qty_concrete_rebar", "Deck concrete volume against reinforcement weight (independent scales)", "fig:qty-concrete-rebar"),
    ]:
        path = (fig_paths or {}).get(key)
        if not path:
            continue
        figures.append(
            r"""\begin{figure}[H]
\centering
\includegraphics[width=0.93\linewidth]{""" + path + r"""}
\caption{""" + caption + r"""}
\label{""" + label + r"""}
\end{figure}"""
        )
    chart_block = ("\n".join(figures) + "\n") if figures else ""

    colspec = "|C{1.0cm}|L{4.6cm}|C{2.6cm}|C{1.4cm}|C{1.6cm}|C{1.6cm}|C{1.8cm}|"

    return r"""
\chapter{Material Take-off \& Quantity Summary}
\label{ch:material-takeoff}

This chapter converts the designed geometry into a bill of quantities: the
volume of every steel and concrete component, the number of units, and the
resulting tonnage. Section~7.1 lists each item with the arithmetic that
produced it; Section~7.2 rolls the line items up into the three totals a
quantity surveyor prices (structural steel, deck concrete, reinforcement); and
Section~7.3 plots those totals for at-a-glance comparison.

\section{Bill of Materials}
\label{sec:boq}

\begin{longtable}{""" + colspec + r"""}
\caption{Bill of materials --- steel, concrete and reinforcement quantities}\label{tab:boq}\\
\hline
\textbf{S.N.} & \textbf{Item Description} & \textbf{Volume (m$^3$)} & \textbf{Qty} & \textbf{Total Volume (m$^3$)} & \textbf{Weight (MT)} & \textbf{Total Weight (MT)} \\
\hline
""" + "\n".join(rows) + r"""
\hline
\end{longtable}

""" + note("Volume arithmetic is quoted per unit; ``Quantity`` is the number of "
            "such units in the bridge. Weights use $\\rho_{steel} = 7.85$ t/m$^3$ "
            "for steel and $\\rho_{concrete} = 2.50$ t/m$^3$ for concrete.") + r"""

\section{Quantity Roll-up}
\label{sec:boq-totals}

\begin{longtable}{|L{9.4cm}|C{3.4cm}|C{3.2cm}|}
\caption{Rolled-up quantities for pricing}\label{tab:boq-totals}\\
\hline
\textbf{Item} & \textbf{Quantity} & \textbf{Unit} \\
\hline
""" + "\n".join(rollup_rows) + r"""
\hline
\end{longtable}

""" + note("Reinforcement content is derived from the deck concrete volume at the "
            "design reinforcement rate; it is indicative for pricing, not a bar "
            "bending schedule.") + r"""

\clearpage
\section{Quantity Charts}
\label{sec:boq-charts}

The two charts below plot the same numbers as Tables~\ref{tab:boq} and
\ref{tab:boq-totals}. The first ranks the steel components by tonnage so the
dominant contributors are obvious; the second places deck concrete volume and
reinforcement weight side by side, since those two drive the deck slab cost.

\vspace{0.6em}
""" + chart_block + r"""
"""
