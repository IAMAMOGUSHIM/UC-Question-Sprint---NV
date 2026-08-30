"""
UC Admission-Rate Gap Dashboard
Question: How did the admission-rate gap between California and international
applicants change at each UC campus from 2018-2024?
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Palette (validated categorical / diverging / status colors)
# ----------------------------------------------------------------------------
CAT_COLORS = {
    "Berkeley": "#2a78d6",       # slot 1 blue
    "Davis": "#eb6834",          # slot 2 orange
    "Irvine": "#1baf7a",         # slot 3 aqua
    "Los Angeles": "#eda100",    # slot 4 yellow
    "Merced": "#e87ba4",         # slot 5 magenta
    "Riverside": "#008300",      # slot 6 green
    "San Diego": "#4a3aa7",      # slot 7 violet
    "Santa Barbara": "#e34948",  # slot 8 red
    "Santa Cruz": "#6b5a3f",     # 9th entity folded to a distinct neutral-brown
}
SYSTEMWIDE_COLOR = "#898781"  # muted ink - reference line, not a peer campus
DIVERGE_POS = "#2a78d6"   # blue = California admitted at a relatively higher rate
DIVERGE_NEG = "#e34948"   # red  = International admitted at a relatively higher rate
DIVERGE_MID = "#f0efec"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"

CAMPUS_ORDER = [
    "Berkeley", "Davis", "Irvine", "Los Angeles", "Merced",
    "Riverside", "San Diego", "Santa Barbara", "Santa Cruz",
]

st.set_page_config(page_title="UC Admission-Rate Gap: California vs. International", layout="wide")


# ----------------------------------------------------------------------------
# Data loading + gap computation
# ----------------------------------------------------------------------------
@st.cache_data
def load_gap_table():
    df = pd.read_csv("data/uc_admissions_summary_by_ethnicity.csv")

    # California proxy: this dataset only records residency for "International";
    # every other ethnicity row is a domestic applicant. UC's domestic freshman
    # pool is overwhelmingly California residents, so "Domestic" (all non
    # -International ethnicities summed) is used here as the California proxy.
    # This is an approximation, not a true CA-residency flag - see the note
    # in the app.
    domestic = (
        df[df.ethnicity != "International"]
        .groupby(["entrant_level", "campus", "fall_term", "count_type"], as_index=False)["n"]
        .sum()
    )
    domestic["group"] = "California (proxy)"

    intl = df[df.ethnicity == "International"][
        ["entrant_level", "campus", "fall_term", "count_type", "n"]
    ].copy()
    intl["group"] = "International"

    combined = pd.concat([domestic, intl], ignore_index=True)
    pivot = combined.pivot_table(
        index=["entrant_level", "campus", "fall_term", "group"],
        columns="count_type",
        values="n",
    ).reset_index()
    pivot["admit_rate"] = pivot["Adm"] / pivot["App"]

    wide = pivot.pivot_table(
        index=["entrant_level", "campus", "fall_term"],
        columns="group",
        values=["admit_rate", "App", "Adm"],
    )
    wide.columns = ["_".join(c).strip() for c in wide.columns]
    wide = wide.reset_index()
    wide["gap_pp"] = (
        wide["admit_rate_California (proxy)"] - wide["admit_rate_International"]
    ) * 100
    return wide


gap_all = load_gap_table()

# ----------------------------------------------------------------------------
# Sidebar filters
# ----------------------------------------------------------------------------
st.sidebar.header("Filters")
entrant_level = st.sidebar.radio("Applicant type", ["freshman", "transfer"], index=0)

year_min, year_max = 2018, 2024
years_available = sorted(gap_all.loc[gap_all.entrant_level == entrant_level, "fall_term"].unique())
years_available = [y for y in years_available if year_min <= y <= year_max]
start_year, end_year = st.sidebar.select_slider(
    "Year range", options=years_available, value=(years_available[0], years_available[-1])
)

show_systemwide = st.sidebar.checkbox("Show Systemwide reference line", value=True)
campus_selection = st.sidebar.multiselect(
    "Campuses in trend chart (max 8)",
    options=CAMPUS_ORDER,
    default=["Berkeley", "Los Angeles", "San Diego", "Davis", "Irvine"],
)
if len(campus_selection) > 8:
    st.sidebar.warning("Showing first 8 selected campuses.")
    campus_selection = campus_selection[:8]

st.sidebar.markdown(
    "---\n**Methodology note:** this dataset records residency only for "
    "*International* applicants. \"California\" here is a **proxy**: all "
    "domestic ethnicity categories summed together. It includes any "
    "out-of-state U.S. residents in the file (a small share of UC's "
    "domestic pool), so true CA-resident-only rates would differ slightly."
)

# ----------------------------------------------------------------------------
# Filtered frame
# ----------------------------------------------------------------------------
df = gap_all[
    (gap_all.entrant_level == entrant_level)
    & (gap_all.fall_term >= start_year)
    & (gap_all.fall_term <= end_year)
].copy()

campus_df = df[df.campus != "Systemwide"]
sw_df = df[df.campus == "Systemwide"].sort_values("fall_term")

# ----------------------------------------------------------------------------
# Header + KPIs
# ----------------------------------------------------------------------------
st.title("UC Admission-Rate Gap: California vs. International Applicants")
st.caption(
    f"Gap = California admit rate − International admit rate (percentage points), "
    f"{entrant_level} applicants, {start_year}-{end_year}."
)

sw_start = sw_df[sw_df.fall_term == start_year]["gap_pp"].values
sw_end = sw_df[sw_df.fall_term == end_year]["gap_pp"].values

k1, k2, k3, k4 = st.columns(4)
if len(sw_start) and len(sw_end):
    k1.metric(f"Systemwide gap, {start_year}", f"{sw_start[0]:.1f} pp")
    k2.metric(f"Systemwide gap, {end_year}", f"{sw_end[0]:.1f} pp", f"{sw_end[0]-sw_start[0]:+.1f} pp")

change_by_campus = (
    campus_df[campus_df.fall_term.isin([start_year, end_year])]
    .pivot_table(index="campus", columns="fall_term", values="gap_pp")
)
if start_year in change_by_campus.columns and end_year in change_by_campus.columns:
    change_by_campus["change"] = change_by_campus[end_year] - change_by_campus[start_year]
    change_by_campus = change_by_campus.dropna(subset=["change"]).sort_values("change")
    if not change_by_campus.empty:
        widened = change_by_campus.index[-1]
        narrowed = change_by_campus.index[0]
        k3.metric(f"Widened most ({start_year}→{end_year})", widened, f"{change_by_campus.loc[widened,'change']:+.1f} pp")
        k4.metric(f"Narrowed most ({start_year}→{end_year})", narrowed, f"{change_by_campus.loc[narrowed,'change']:+.1f} pp")

st.divider()

# ----------------------------------------------------------------------------
# Heatmap: campus x year gap
# ----------------------------------------------------------------------------
st.subheader("Gap by campus and year")

heat_rows = CAMPUS_ORDER + (["Systemwide"] if show_systemwide else [])
heat_df = df[df.campus.isin(heat_rows)]
heat_pivot = heat_df.pivot_table(index="campus", columns="fall_term", values="gap_pp").reindex(heat_rows)

max_abs = max(1.0, heat_pivot.abs().max().max())
fig_heat = go.Figure(
    data=go.Heatmap(
        z=heat_pivot.values,
        x=[str(c) for c in heat_pivot.columns],
        y=heat_pivot.index,
        colorscale=[[0, DIVERGE_NEG], [0.5, DIVERGE_MID], [1, DIVERGE_POS]],
        zmid=0,
        zmin=-max_abs,
        zmax=max_abs,
        text=[[f"{v:.1f}" if pd.notna(v) else "" for v in row] for row in heat_pivot.values],
        texttemplate="%{text}",
        textfont={"size": 11, "color": INK_PRIMARY},
        hovertemplate="%{y}, %{x}<br>Gap: %{z:.1f} pp<extra></extra>",
        colorbar=dict(title="pp", outlinewidth=0),
    )
)
fig_heat.update_layout(
    height=420,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(color=INK_SECONDARY),
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig_heat, use_container_width=True)
st.caption("Blue = California admitted at a relatively higher rate. Red = International admitted at a relatively higher rate.")

st.divider()

# ----------------------------------------------------------------------------
# Trend line chart
# ----------------------------------------------------------------------------
st.subheader("Gap trend over time")

fig_line = go.Figure()
fig_line.add_hline(y=0, line=dict(color=AXIS, width=1))

for campus in campus_selection:
    d = campus_df[campus_df.campus == campus].sort_values("fall_term")
    if d.empty:
        continue
    fig_line.add_trace(
        go.Scatter(
            x=d.fall_term,
            y=d.gap_pp,
            mode="lines+markers",
            name=campus,
            line=dict(color=CAT_COLORS.get(campus, INK_MUTED), width=2),
            marker=dict(size=7),
            hovertemplate=f"{campus}, " + "%{x}<br>Gap: %{y:.1f} pp<extra></extra>",
        )
    )

if show_systemwide and not sw_df.empty:
    fig_line.add_trace(
        go.Scatter(
            x=sw_df.fall_term,
            y=sw_df.gap_pp,
            mode="lines",
            name="Systemwide",
            line=dict(color=SYSTEMWIDE_COLOR, width=2, dash="dash"),
            hovertemplate="Systemwide, %{x}<br>Gap: %{y:.1f} pp<extra></extra>",
        )
    )

fig_line.update_layout(
    height=440,
    margin=dict(l=10, r=10, t=10, b=10),
    plot_bgcolor="#fcfcfb",
    paper_bgcolor="#fcfcfb",
    font=dict(color=INK_SECONDARY),
    hovermode="x unified",
    xaxis=dict(title="Fall term", gridcolor=GRID, dtick=1),
    yaxis=dict(title="Gap (pp)", gridcolor=GRID, zeroline=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)
st.plotly_chart(fig_line, use_container_width=True)

st.divider()

# ----------------------------------------------------------------------------
# Change bar chart
# ----------------------------------------------------------------------------
st.subheader(f"Change in gap, {start_year} → {end_year}")

if not change_by_campus.empty:
    sorted_change = change_by_campus.sort_values("change")
    colors = [DIVERGE_POS if v >= 0 else DIVERGE_NEG for v in sorted_change["change"]]
    fig_bar = go.Figure(
        go.Bar(
            x=sorted_change["change"],
            y=sorted_change.index,
            orientation="h",
            marker_color=colors,
            text=[f"{v:+.1f}" for v in sorted_change["change"]],
            textposition="outside",
            hovertemplate="%{y}<br>Change: %{x:+.1f} pp<extra></extra>",
        )
    )
    fig_bar.update_layout(
        height=380,
        margin=dict(l=10, r=30, t=10, b=10),
        plot_bgcolor="#fcfcfb",
        paper_bgcolor="#fcfcfb",
        font=dict(color=INK_SECONDARY),
        xaxis=dict(title="Change in gap (pp)", gridcolor=GRID, zeroline=True, zerolinecolor=AXIS),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption("Positive = the California-vs-International gap widened over the period. Negative = it narrowed.")
else:
    st.info("Not enough data to compute a start-to-end change for this selection.")

st.divider()

# ----------------------------------------------------------------------------
# Detail table
# ----------------------------------------------------------------------------
with st.expander("Underlying numbers"):
    table = df[
        [
            "campus", "fall_term",
            "admit_rate_California (proxy)", "admit_rate_International", "gap_pp",
            "App_California (proxy)", "Adm_California (proxy)",
            "App_International", "Adm_International",
        ]
    ].sort_values(["campus", "fall_term"]).rename(columns={
        "admit_rate_California (proxy)": "CA admit rate",
        "admit_rate_International": "Intl admit rate",
        "gap_pp": "Gap (pp)",
        "App_California (proxy)": "CA applicants",
        "Adm_California (proxy)": "CA admits",
        "App_International": "Intl applicants",
        "Adm_International": "Intl admits",
    })
    st.dataframe(table, use_container_width=True, hide_index=True)
