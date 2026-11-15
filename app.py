import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy.ndimage import median_filter

from analysis import load_analysis, polygon_boundary_coordinates


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="NISAR Wildfire Explorer",
    page_icon="🌍",
    layout="wide"
)

st.markdown("""
<style>
    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    [data-testid="stMetric"] {
        background: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 16px;
        border-radius: 12px;
    }
    .small-note {
        font-size: 0.85rem;
        opacity: 0.75;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================
# LOAD ANALYSIS
# ==================================================

@st.cache_data(show_spinner="Processing NISAR radar data...")
def get_analysis():
    return load_analysis()


try:
    results = get_analysis()
except Exception as error:
    st.error(f"Could not load the NISAR data: {error}")
    st.stop()


# ==================================================
# HEADER
# ==================================================

st.title("🌍 NISAR Wildfire Explorer")

st.markdown(
    """
    ### Exploring radar-observed surface changes associated with a wildfire

    An interactive study of the September 2026 Aksu wildfire
    in Antalya, Türkiye, using NASA–ISRO NISAR L-band observations.
    This is a surface-change exploration, not an automated burned-area detector.
    """
)

st.caption(
    "Study event: 7–10 September 2026  ·  "
    "Sensor: NISAR L-band  ·  "
    "Product: GCOV Provisional"
)

st.divider()


# ==================================================
# INCIDENT OVERVIEW
# ==================================================

st.header("Incident overview")

st.markdown(
    """
    The wildfire began near Karaöz in Aksu on 7 September 2026.
    It spread towards neighbouring areas, including Kepez.
    Strong winds contributed to the spread and evacuation measures.
    """
)

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric("Mapped fire perimeter", "3,913 ha")
metric2.metric("Homes evacuated", "254")
metric3.metric("People affected", "47")
metric4.metric("Volunteer firefighter deaths", "1")

st.caption(
    "These figures come from external reporting and satellite-derived "
    "perimeter information, not from NISAR. Sources and qualifications "
    "are provided in the Fire impact section."
)


# ==================================================
# SIDEBAR: RADAR EXPLORER CONTROLS
# ==================================================

st.sidebar.title("Radar explorer")

smooth_display = st.sidebar.checkbox(
    "Apply 3×3 median filter to map display",
    value=False,
    help="Display-only smoothing. Statistics always use the original unsmoothed data."
)

polarization = st.sidebar.selectbox(
    "Polarization",
    ["HH", "HV"]
)

display_mode = st.sidebar.radio(
    "Visualization",
    [
        "Original backscatter",
        "Backscatter change",
        "Candidate change areas"
    ]
)

if display_mode == "Original backscatter":
    selected_date = st.sidebar.selectbox(
        "Acquisition date",
        results["dates"]
    )
else:
    selected_comparison = st.sidebar.selectbox(
        "Date comparison",
        results["comparisons"]
    )


# ==================================================
# PREPARE PLOT DATA
# ==================================================

if polarization == "HH":
    db_data = results["hh_db"]
    common_mask = results["common_valid_hh"]
else:
    db_data = results["hv_db"]
    common_mask = results["common_valid_hv"]

left, right, bottom, top = results["extent"]
rows, cols = common_mask.shape

# Pixel-centre coordinates.
x_coordinates = np.linspace(
    left + (right - left) / (2 * cols),
    right - (right - left) / (2 * cols),
    cols
)

y_coordinates = np.linspace(
    bottom + (top - bottom) / (2 * rows),
    top - (top - bottom) / (2 * rows),
    rows
)


# ==================================================
# CREATE INTERACTIVE RADAR FIGURE
# ==================================================

fig = go.Figure()

if display_mode == "Original backscatter":

    data = np.ma.masked_where(
        ~common_mask,
        db_data[selected_date]
    )

    # First raster row is northernmost; reverse rows for Plotly's
    # ascending y coordinates.
    z = np.flipud(data.filled(np.nan))

    all_values = np.concatenate([
        db_data[date][common_mask]
        for date in results["dates"]
    ])

    vmin = float(np.percentile(all_values, 2))
    vmax = float(np.percentile(all_values, 98))

    fig.add_trace(
        go.Heatmap(
            x=x_coordinates,
            y=y_coordinates,
            z=z,
            colorscale="Greys",
            zmin=vmin,
            zmax=vmax,
            colorbar=dict(title="Backscatter<br>(dB)"),
            hovertemplate=(
                "Easting: %{x:.0f} m<br>"
                "Northing: %{y:.0f} m<br>"
                "Backscatter: %{z:.2f} dB"
                "<extra></extra>"
            )
        )
    )

    figure_title = f"{polarization} backscatter — {selected_date}"

else:

    change = results["change_maps"][
        polarization
    ][selected_comparison]

    candidate = results["candidate_results"][
        polarization
    ][selected_comparison]

    # Optional display-only smoothing. The underlying change array and all
    # statistics remain untouched. Fill invalid cells before filtering, then
    # restore the invalid mask so the filter does not create data there.
    display_change = change.copy()

    if smooth_display:
        valid_values = change[common_mask]
        fill_value = float(np.median(valid_values))
        filled = np.where(common_mask, change, fill_value)
        display_change = median_filter(
            filled,
            size=3,
            mode="nearest"
        )
        display_change = np.where(
            common_mask,
            display_change,
            np.nan
        )

    z = np.flipud(
        np.where(common_mask, display_change, np.nan)
    )

    limit = float(np.percentile(
        np.abs(display_change[common_mask]),
        98
    ))

    if limit == 0:
        limit = 0.001

    fig.add_trace(
        go.Heatmap(
            x=x_coordinates,
            y=y_coordinates,
            z=z,
            colorscale="RdBu",
            reversescale=True,
            zmin=-limit,
            zmax=limit,
            zmid=0,
            colorbar=dict(title="Change<br>(dB)"),
            hovertemplate=(
                "Easting: %{x:.0f} m<br>"
                "Northing: %{y:.0f} m<br>"
                "Change: %{z:.2f} dB"
                "<extra></extra>"
            )
        )
    )

    if display_mode == "Candidate change areas":

        candidate_z = np.flipud(
            np.where(candidate["mask"], 1.0, np.nan)
        )

        fig.add_trace(
            go.Heatmap(
                x=x_coordinates,
                y=y_coordinates,
                z=candidate_z,
                colorscale=[
                    [0, "rgba(255, 140, 0, 0.85)"],
                    [1, "rgba(255, 140, 0, 0.85)"]
                ],
                zmin=0,
                zmax=1,
                showscale=False,
                hoverinfo="skip",
                name="Candidate changes"
            )
        )

    figure_title = (
        f"{polarization} {display_mode.lower()} "
        f"— {selected_comparison}"
    )


# ==================================================
# ADD EXTERNAL FIRE-PERIMETER REFERENCE
# ==================================================

if results["perimeter_geometry_utm"] is not None:
    perimeter_x, perimeter_y = polygon_boundary_coordinates(
        results["perimeter_geometry_utm"]
    )

    fig.add_trace(
        go.Scatter(
            x=perimeter_x,
            y=perimeter_y,
            mode="lines",
            line=dict(color="#FF8C42", width=2.5),
            name="External mapped fire perimeter",
            hoverinfo="skip"
        )
    )


# ==================================================
# ADD APPROXIMATE NEIGHBOURHOOD REFERENCE LOCATIONS
# ==================================================

fire_x = []
fire_y = []
fire_names = []
outside_locations = []

for name, point in results["fire_projected"].items():
    if point["inside"]:
        fire_x.append(point["x"])
        fire_y.append(point["y"])
        fire_names.append(name)
    else:
        outside_locations.append(name)

if fire_x:
    fig.add_trace(
        go.Scatter(
            x=fire_x,
            y=fire_y,
            mode="markers+text",
            text=fire_names,
            textposition="top right",
            marker=dict(
                size=11,
                color="#FFD43B",
                line=dict(color="#222222", width=1.5),
                symbol="circle"
            ),
            name="Neighbourhood centres",
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Easting: %{x:.0f} m<br>"
                "Northing: %{y:.0f} m"
                "<extra></extra>"
            )
        )
    )


# ==================================================
# FINAL FIGURE LAYOUT
# ==================================================

fig.update_layout(
    title=dict(
        text=figure_title,
        x=0.02,
        xanchor="left"
    ),
    height=680,
    autosize=True,
    uirevision="nisar-radar-view",
    template="plotly_dark",
    margin=dict(l=20, r=20, t=70, b=20),
    hovermode="closest",
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

fig.update_xaxes(
    title="Easting (metres)",
    range=[left, right],
    showgrid=True,
    gridcolor="rgba(150,150,150,0.15)"
)

fig.update_yaxes(
    title="Northing (metres)",
    range=[bottom, top],
    scaleanchor="x",
    scaleratio=1,
    showgrid=True,
    gridcolor="rgba(150,150,150,0.15)"
)


# ==================================================
# RADAR EXPLORER DISPLAY
# ==================================================

st.header("Radar change explorer")

st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "responsive": True,
        "scrollZoom": True,
        "displaylogo": False,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "nisar_radar_analysis"
        }
    }
)

if results["perimeter_status"] == "loaded":
    st.caption(
        "Orange outline: independently mapped external fire perimeter. "
        "It is contextual reference data, not a boundary detected by NISAR."
    )
else:
    st.warning(
        "No fire-perimeter GeoJSON was found. Add "
        "datasets/aksu_fire_perimeter.geojson to enable the perimeter overlay "
        "and inside/outside comparison. The current maps remain NISAR-only."
    )

st.caption(
    "Yellow markers show approximate neighbourhood centres. "
    "They are geographic reference points, not fire ignition points "
    "or a verified burned-area boundary."
)

if outside_locations:
    st.warning(
        "These reference locations fall outside the selected NISAR "
        "raster area: " + ", ".join(outside_locations)
    )

st.caption(
    f"Extracted NISAR region: {results['roi_shape'][1]} columns × "
    f"{results['roi_shape'][0]} rows | "
    f"Pixel spacing: {results['pixel_spacing'][0]:.0f} m"
)


# ==================================================
# RADAR STATISTICS
# ==================================================

if display_mode != "Original backscatter":

    stats = results["statistics"][
        polarization
    ][selected_comparison]

    candidate = results["candidate_results"][
        polarization
    ][selected_comparison]

    st.subheader("Quantitative analysis")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Mean change", f"{stats['mean']:.3f} dB")
    c2.metric("Median change", f"{stats['median']:.3f} dB")
    c3.metric("Pixels increased", f"{stats['increased']:.1f}%")
    c4.metric("Candidate pixels", f"{candidate['percentage']:.2f}%")

    with st.expander("Threshold details"):

        st.write(
            f"Median Absolute Deviation: {candidate['mad']:.4f} dB"
        )

        st.write(
            f"Robust standard deviation: "
            f"{candidate['robust_std']:.4f} dB"
        )

        st.write(
            f"Lower threshold: "
            f"{candidate['lower_threshold']:.4f} dB"
        )

        st.write(
            f"Upper threshold: "
            f"{candidate['upper_threshold']:.4f} dB"
        )

        st.write(
            "Candidate pixels are unusually changed pixels "
            "according to the selected statistical threshold. "
            "They are not confirmed burned pixels."
        )


# ==================================================
# PERIMETER-BASED EXPLORATORY COMPARISON
# ==================================================

if (
    display_mode != "Original backscatter"
    and results["perimeter_status"] == "loaded"
):
    st.subheader("Inside vs. outside the mapped fire perimeter")

    region_stats = results["perimeter_statistics"][
        polarization
    ][selected_comparison]

    inside = region_stats["inside"]
    outside = region_stats["outside"]

    if inside["pixels"] == 0 or outside["pixels"] == 0:
        st.warning(
            "The perimeter or its complement contains no valid pixels in this "
            "selected NISAR region, so the comparison cannot be calculated."
        )
    else:
        comparison_table = {
            "Region": [
                "Inside mapped perimeter",
                "Outside mapped perimeter"
            ],
            "Valid pixels": [
                inside["pixels"],
                outside["pixels"]
            ],
            "Median change (dB)": [
                inside["median"],
                outside["median"]
            ],
            "Mean change (dB)": [
                inside["mean"],
                outside["mean"]
            ],
            "25th percentile (dB)": [
                inside["p25"],
                outside["p25"]
            ],
            "75th percentile (dB)": [
                inside["p75"],
                outside["p75"]
            ],
        }

        st.dataframe(
            comparison_table,
            use_container_width=True,
            hide_index=True
        )

        st.caption(
            "Exploratory comparison only. The outside region is not a matched "
            "control group; land cover, moisture, terrain and other conditions "
            "may differ. The perimeter is external reference data and is not "
            "used to train or validate a burned-area classifier."
        )


# ==================================================
# FIRE IMPACT
# ==================================================

st.divider()
st.header("Fire impact and affected communities")

impact1, impact2 = st.columns(2)

with impact1:
    st.subheader("Human impact")
    st.markdown("""
    - **47 people affected**, according to the Antalya Governor's
      statement reported on 9 September.
    - **11 people taken to hospital** and 36 treated as outpatients,
      according to the same report.
    - **One volunteer firefighter died** after suffering a
      smoke-related heart attack, according to Associated Press.
    - More than **100 dogs were evacuated** from an animal shelter.
    """)

with impact2:
    st.subheader("Homes and infrastructure")
    st.markdown("""
    - **254 homes evacuated** during the initial response.
    - **3 buildings** assessed as requiring urgent demolition.
    - **13 buildings** reported with minor damage.
    - Power outages affected more than **2,000 homes**, according
      to Associated Press.
    - The Antalya–Isparta road and parts of the northern ring road
      were temporarily closed.
    """)

st.info(
    "Financial losses: a consolidated monetary damage estimate "
    "was not identified in the sources used for this application. "
    "No financial figure is inferred from the burned-area estimate."
)


# ==================================================
# FIRE TIMELINE
# ==================================================

st.divider()
st.header("Event and satellite timeline")

timeline = [
    ("27 August 2026", "NISAR pre-fire baseline acquisition."),
    ("7 September 2026", "Fire reported near Karaöz, Aksu."),
    ("8 September 2026", "NISAR acquisition during the active-fire period."),
    ("9 September 2026", "The fire was reported largely under control."),
    (
        "20 September 2026",
        "NISAR post-event acquisition, ten days after "
        "the reported control date of 10 September."
    )
]

for date, description in timeline:
    with st.container(border=True):
        st.markdown(f"**{date}**")
        st.write(description)


# ==================================================
# ENVIRONMENTAL CONTEXT
# ==================================================

st.divider()
st.header("Environmental context")

st.markdown("""
The satellite-derived fire record reports approximately **3,913 hectares**
of burned area across Aksu, Kepez and Döşemealtı.

Reported land-cover composition within the perimeter:

- Coniferous forest: 51%
- Scrub and transitional woodland: 33%
- Agricultural areas: 6.2%
- Mixed forest: 3.3%
- Other natural land: 2.9%
- Artificial surfaces: 1.8%
- Broadleaved forest: 1.2%

These figures describe land cover inside the mapped perimeter. They
should not be interpreted as a field-verified measurement of the
damage to every individual land parcel.
""")


# ==================================================
# METHODOLOGY AND LIMITATIONS
# ==================================================

st.divider()
st.header("How this application works")

with st.expander("1. What does NISAR measure?"):
    st.write("""
    NISAR is a radar Earth-observation mission. Its L-band radar
    transmits microwave signals and measures the energy returned
    from Earth's surface.

    HH and HV represent different transmit/receive polarizations.
    Their backscatter responses can help reveal changes in vegetation,
    soil and surface structure.
    """)

with st.expander("2. How is radar change calculated?"):
    st.latex(
        r"\Delta \sigma^0_{dB} = "
        r"\sigma^0_{after,dB} - "
        r"\sigma^0_{before,dB}"
    )

    st.write("""
    Positive values indicate increased backscatter; negative values
    indicate decreased backscatter. Neither direction alone proves
    that a pixel was burned.
    """)

with st.expander("3. How are candidate changes identified?"):
    st.write("""
    The application calculates the median and Median Absolute
    Deviation (MAD) of valid pixel changes. It flags values more
    than three robust standard deviations from the median.

    This is an exploratory statistical change detector, not a
    validated wildfire classifier. The threshold is calculated over
    the full valid study area, not tuned to the mapped fire perimeter.
    """)

with st.expander("4. Important limitations"):
    st.markdown("""
    - Radar changes can be caused by moisture, rainfall, vegetation,
      roughness and other surface conditions.
    - Candidate pixels are not confirmed burned pixels.
    - The four reference locations are approximate neighbourhood centres.
    - If supplied, the perimeter is an external reference; it is not
      detected by NISAR and is not a field-verified damage boundary.
    - The NISAR ROI is not the same thing as the complete
      3,913-hectare EFFIS perimeter.
    - The analysis uses three acquisitions, so it cannot describe
      every stage of the fire.
    - The selected NISAR data are labelled Provisional.
    - Median filtering, when enabled, changes map appearance only; all
      statistics are calculated from unsmoothed radar data.
    """)


# ==================================================
# SOURCES
# ==================================================

st.divider()
st.header("Sources and further reading")

st.markdown("""
**Fire reporting**

- [Anadolu Agency / Habertürk — Aksu and Kepez fire, 9 September 2026](https://www.haberturk.com/gundem/aksu-ve-kepez-deki-orman-yangini-buyuk-olcude-kontrol-altina-alindi-3911437)
- [TRT Haber — Antalya fire and evacuations, 8 September 2026](https://www.trthaber.com/haber/turkiye/antalyanin-2-farkli-bolgesinde-yangin-956180.html)
- [Associated Press — Volunteer firefighter death and emergency response](https://apnews.com/article/2b6a436287753383fd76c854cb424f60)

**Satellite-derived fire information**

- [WorldFires — Aksu fire, September 2026](https://worldfires.org/en/fire/aksu-antalya-2026-09)
- [NASA FIRMS — Fire Information for Resource Management System](https://firms.modaps.eosdis.nasa.gov/)
- [Copernicus Emergency Management Service](https://emergency.copernicus.eu/)

**NISAR mission**

- [NASA NISAR mission](https://nisar.jpl.nasa.gov/)
""")

st.caption(
    "NISAR radar analysis and external incident information are "
    "presented as separate evidence sources. This application is "
    "an exploratory educational tool, not an official damage "
    "assessment or emergency-management system."
)