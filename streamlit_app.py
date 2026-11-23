
from pathlib import Path
import html

import pandas as pd
import geopandas as gpd
import streamlit as st
import folium
from branca.colormap import LinearColormap
from folium.plugins import MarkerCluster, Fullscreen, MeasureControl
from streamlit_folium import st_folium


st.set_page_config(
    page_title="Camden Food Assistance Location Planning Platform",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR

st.markdown(
    """
    <style>
      .stApp { background:#f5f3ed; }
      .block-container { max-width:1550px; padding-top:1.4rem; padding-bottom:3rem; }
      [data-testid="stSidebar"] { background:#fff; border-right:1px solid #d9ddd8; }
      .kicker { color:#cc0033; font-size:.75rem; font-weight:700; letter-spacing:.1em; text-transform:uppercase; }
      .lede { color:#5e6b66; max-width:950px; font-size:1.02rem; }
      .warning { background:#fff1c9; color:#5b3b00; border-left:5px solid #e1a52b; padding:.8rem 1rem; border-radius:0 .5rem .5rem 0; margin:.7rem 0 1rem; }
      .insight { background:#fff; border:1px solid #d9ddd8; border-radius:.7rem; padding:1rem; margin-bottom:.75rem; }
      .action { background:#e8f3ef; border-left:5px solid #0b6e4f; padding:.85rem; border-radius:0 .5rem .5rem 0; }
      .caution { background:#fff2db; color:#684600; border-left:5px solid #e7a32f; padding:.8rem; border-radius:0 .5rem .5rem 0; }
      div[data-testid="stMetric"] { background:#fff; border:1px solid #d9ddd8; border-radius:.65rem; padding:.75rem 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data():
    tracts = gpd.read_file(DATA_DIR / "camden_tracts.geojson")
    master = pd.read_csv(DATA_DIR / "tract_master.csv", dtype={"geoid": str})
    services = pd.read_csv(
        DATA_DIR / "service_locations.csv",
        dtype={"service_location_id": str, "assigned_geoid": str, "phone": str},
    )
    tract_crs = tracts.crs
    tracts["geoid"] = tracts["geoid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)
    master["geoid"] = master["geoid"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)

    # Bring every master-table measure into the mapped tract data.
    missing_master_columns = [
        column for column in master.columns
        if column not in tracts.columns and column != "geometry"
    ]
    if missing_master_columns:
        tracts = tracts.merge(
            master[["geoid"] + missing_master_columns],
            on="geoid",
            how="left",
            validate="one_to_one",
        )
        tracts = gpd.GeoDataFrame(tracts, geometry="geometry", crs=tract_crs)

    # Derive percentage-of-all-households measures.
    total_households = pd.to_numeric(tracts["acs_total_households_est"], errors="coerce")
    children_households = pd.to_numeric(tracts["acs_snap_households_with_children_est"], errors="coerce")
    senior_households = pd.to_numeric(tracts["acs_snap_households_with_senior_est"], errors="coerce")
    children_pct = children_households.div(total_households).mul(100).where(total_households > 0)
    senior_pct = senior_households.div(total_households).mul(100).where(total_households > 0)

    if "snap_children_pct_all_households" not in tracts.columns:
        tracts["snap_children_pct_all_households"] = children_pct
    else:
        tracts["snap_children_pct_all_households"] = pd.to_numeric(
            tracts["snap_children_pct_all_households"], errors="coerce"
        ).fillna(children_pct)

    if "snap_senior_pct_all_households" not in tracts.columns:
        tracts["snap_senior_pct_all_households"] = senior_pct
    else:
        tracts["snap_senior_pct_all_households"] = pd.to_numeric(
            tracts["snap_senior_pct_all_households"], errors="coerce"
        ).fillna(senior_pct)
    # --------------------------------------------------------
      # Calculate households without broadband
      # --------------------------------------------------------

    broadband_subscription_pct = pd.to_numeric(
        tracts["acs_broadband_subscription_pct"],
        errors="coerce"
    )

    calculated_no_broadband_pct = (
        100 - broadband_subscription_pct
    ).clip(0, 100)

    if "no_broadband_subscription_pct" not in tracts.columns:

        tracts["no_broadband_subscription_pct"] = (
            calculated_no_broadband_pct
        )

    else:

        tracts["no_broadband_subscription_pct"] = (
            pd.to_numeric(
                tracts["no_broadband_subscription_pct"],
                errors="coerce"
            )
            .fillna(calculated_no_broadband_pct)
        )
    return tracts, master, services


tracts, tract_master, services = load_data()
tracts = tracts.sort_values("research_priority_rank").reset_index(drop=True)


MEASURES = {
    "Adult food-insecurity prevalence": {
        "field": "places_food_insecurity_pct", "format": "percent", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "Modeled percentage of adults experiencing food insecurity.",
        "reading": "Higher values indicate greater modeled prevalence, not an observed count of clients.",
    },
    "Modeled research priority index": {
        "field": "research_priority_index", "format": "number", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "A combined planning screen reflecting modeled need and relative service-access shortfall.",
        "reading": "Higher values warrant earlier investigation; they do not approve a site or predict demand.",
    },
    "SNAP households with children (% of all households)": {
        "field": "snap_children_pct_all_households", "format": "percent", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "Estimated SNAP households with children divided by all households in the tract.",
        "reading": "Higher values suggest a larger family-oriented outreach context; they are not counts of children.",
    },
    "SNAP households with seniors (% of all households)": {
        "field": "snap_senior_pct_all_households", "format": "percent", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "Estimated SNAP households with a senior divided by all households in the tract.",
        "reading": "Higher values suggest a larger senior-serving context; they are not counts of individual seniors.",
    },
    "Households without a vehicle": {
        "field": "acs_no_vehicle_households_pct", "format": "percent", "attention": "high",
        "colors": ["#ffffcc", "#fed976", "#feb24c", "#fd8d3c", "#f03b20", "#bd0026"],
        "meaning": "Percentage of households reporting no available vehicle.",
        "reading": "Higher values may increase the importance of walkability, delivery, transit and neighborhood-based distribution.",
    },
    "Adults with a disability": {
        "field": "places_disability_pct", "format": "percent", "attention": "high",
        "colors": ["#ffffcc", "#fed976", "#feb24c", "#fd8d3c", "#f03b20", "#bd0026"],
        "meaning": "Modeled percentage of adults reporting a disability.",
        "reading": "Higher values point to accessibility, mobility and communication considerations for service design.",
    },
    "Limited-English context": {
        "field": "acs_limited_english_pct", "format": "percent", "attention": "high",
        "colors": ["#ffffcc", "#fed976", "#feb24c", "#fd8d3c", "#f03b20", "#bd0026"],
        "meaning": "ACS-based limited-English context for the tract.",
        "reading": "Higher values support multilingual outreach and locally appropriate communication planning.",
    },
    "Households without broadband": {
        "field": "no_broadband_subscription_pct", "format": "percent", "attention": "high",
        "colors": ["#ffffcc", "#fed976", "#feb24c", "#fd8d3c", "#f03b20", "#bd0026"],
        "meaning": "Percentage of households without a broadband subscription.",
        "reading": "Higher values suggest that digital-only outreach may miss more residents.",
    },
    "Distance to nearest included service record": {
        "field": "nearest_service_miles", "format": "miles", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "Straight-line distance from the tract reference point to the nearest included service record.",
        "reading": "Higher values indicate weaker proximity, but do not represent walking, driving or transit time.",
    },
    "Included service records within one mile": {
        "field": "services_within_1mi", "format": "integer", "attention": "low",
        "colors": ["#eff3ff", "#c6dbef", "#9ecae1", "#6baed6", "#2171b5", "#084594"],
        "meaning": "Number of included service records within one straight-line mile of the tract reference point.",
        "reading": "Lower values suggest fewer nearby records; the measure does not account for hours, eligibility or capacity.",
    },
    "Modeled relative service access ratio": {
        "field": "relative_access_ratio", "format": "ratio", "attention": "low",
        "colors": ["#fff7fb", "#d0d1e6", "#a6bddb", "#67a9cf", "#1c9099", "#016c59"],
        "meaning": "Modeled service access relative to the Camden benchmark after accounting for nearby need.",
        "reading": "Values below 1 indicate access below the benchmark; values above 1 indicate comparatively stronger modeled access.",
    },
    "Potential relative service gap": {
        "field": "relative_underserved_need_units", "format": "number", "attention": "high",
        "colors": ["#fff7bc", "#fec44f", "#fe9929", "#ec7014", "#cc4c02", "#8c2d04"],
        "meaning": "Modeled food-insecure adults weighted by the relative access shortfall.",
        "reading": "Higher values indicate a larger potential relative gap, not observed unmet demand.",
    },
    "ML tract typology": {
        "field": "ml_cluster", "format": "integer", "attention": "category", "categorical": True,
        "meaning": "An exploratory two-cluster grouping based on need, access disadvantage and outreach barriers.",
        "reading": "The clusters describe similar tract profiles; they do not predict demand or determine a location.",
    },
}


def safe(value):
    if value is None or pd.isna(value):
        return "Not available"
    text = str(value).strip()
    return "Not available" if not text or text.lower() in {"nan", "none"} else html.escape(text)


def format_value(value, kind):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return "Not available"
    if pd.isna(value):
        return "Not available"
    if kind == "percent":
        return f"{value:,.1f}%"
    if kind == "miles":
        return f"{value:,.2f} miles"
    if kind == "integer":
        return f"{int(round(value)):,}"
    if kind == "ratio":
        return f"{value:,.2f}"
    return f"{value:,.1f}"


def service_popup(row):
    return f"""
    <div style='font-family:Arial;font-size:12px;line-height:1.45;width:320px'>
      <div style='font-size:15px;font-weight:bold;color:#0b6e4f'>{safe(row.get('primary_name'))}</div>
      <b>Service type:</b> {safe(row.get('service_types'))}<br>
      <b>Address:</b> {safe(row.get('full_address'))}<br>
      <b>Phone:</b> {safe(row.get('phone'))}<br>
      <b>Recorded schedule:</b> {safe(row.get('schedule_summary'))}<br>
      <b>Source:</b> {safe(row.get('source_names'))}
      <div style='margin-top:8px;background:#fff1e5;border-left:4px solid #d95f02;padding:7px;font-size:10px'>
        Included record only. Confirm operations, eligibility, schedule and capacity directly.
      </div>
    </div>
    """


def planning_interpretation(row):
    need_median = pd.to_numeric(tracts["places_food_insecurity_pct"], errors="coerce").median()
    need = "above" if float(row["places_food_insecurity_pct"]) > need_median else "at or below"
    access = "below" if float(row["relative_access_ratio"]) < 1 else "at or above"
    rank = int(row["research_priority_rank"])
    candidate = "It is in the top-five investigation screen." if rank <= 5 else "It is not in the current top-five screen."
    return (
        f"Food-insecurity prevalence is {need} the Camden tract median, while modeled access is {access} "
        f"the Camden benchmark. {candidate} This combination should guide follow-up investigation, not an automatic siting decision."
    )


def tract_label(geoid):
    row = tracts.loc[tracts["geoid"] == geoid].iloc[0]
    return f"#{int(row['research_priority_rank'])} · {row['neighborhood']} · {row['tract_name']}"


def build_decision_map(selected_measure, selected_geoid, show_candidates, show_services):
    config = MEASURES[selected_measure]
    field = config["field"]
    min_lon, min_lat, max_lon, max_lat = tracts.total_bounds
    camden_map = folium.Map(
        location=[(min_lat + max_lat) / 2, (min_lon + max_lon) / 2],
        zoom_start=12,
        tiles=None,
        control_scale=True,
        prefer_canvas=True,
    )
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
        attr="Esri, HERE, Garmin, USGS, NGA, EPA, USDA, NPS",
        name="Light gray basemap",
        overlay=False,
        control=True,
        show=True,
    ).add_to(camden_map)

    cluster_colors = {1: "#d95f02", 2: "#159a84"}
    color_scale = None
    if not config.get("categorical", False):
        values = pd.to_numeric(tracts[field], errors="coerce").dropna()
        value_min, value_max = float(values.min()), float(values.max())
        if value_min == value_max:
            value_max = value_min + 1
        color_scale = LinearColormap(config["colors"], vmin=value_min, vmax=value_max, caption=selected_measure)

    def measure_style(feature):
        value = feature["properties"].get(field)
        if config.get("categorical", False):
            try:
                fill = cluster_colors.get(int(value), "#bdbdbd")
            except (TypeError, ValueError):
                fill = "#bdbdbd"
        else:
            try:
                fill = color_scale(float(value))
            except (TypeError, ValueError):
                fill = "#bdbdbd"
        return {"fillColor": fill, "color": "#35443e", "weight": 1.3, "fillOpacity": 0.74}

    tract_group = folium.FeatureGroup(name=selected_measure, overlay=True, control=True, show=True)
    for _, tract in tracts.iterrows():
        one_tract = gpd.GeoDataFrame([tract], geometry="geometry", crs=tracts.crs)
        value_display = format_value(tract.get(field), config["format"])
        popup = f"""
        <div style='font-family:Arial;font-size:12px;line-height:1.45;width:360px'>
          <div style='font-size:16px;font-weight:bold'>{safe(tract.get('neighborhood'))}</div>
          <div style='color:#666'>{safe(tract.get('tract_name'))}</div><hr>
          <b>{html.escape(selected_measure)}:</b> {value_display}<br>
          <b>Priority rank:</b> #{format_value(tract.get('research_priority_rank'), 'integer')}<br>
          <b>Food insecurity:</b> {format_value(tract.get('places_food_insecurity_pct'), 'percent')}<br>
          <b>Relative access ratio:</b> {format_value(tract.get('relative_access_ratio'), 'ratio')}<br>
          <b>Potential gap units:</b> {format_value(tract.get('relative_underserved_need_units'), 'number')}<br>
          <b>Nearest included record:</b> {format_value(tract.get('nearest_service_miles'), 'miles')}<br>
          <b>ML typology:</b> {safe(tract.get('ml_typology'))}
          <div style='margin-top:8px;color:#666;font-size:10px'>Planning evidence only; verify local conditions and service operations.</div>
        </div>
        """
        folium.GeoJson(
            one_tract.to_json(),
            style_function=measure_style,
            highlight_function=lambda feature: {"color": "#111", "weight": 3, "fillOpacity": .88},
            tooltip=folium.Tooltip(
                f"<b>{safe(tract.get('neighborhood'))}</b><br>{html.escape(selected_measure)}: {value_display}<br>Priority rank: #{format_value(tract.get('research_priority_rank'), 'integer')}",
                sticky=True,
            ),
            popup=folium.Popup(popup, max_width=430),
            control=False,
        ).add_to(tract_group)
    tract_group.add_to(camden_map)

    selected_feature = tracts.loc[tracts["geoid"] == selected_geoid]
    folium.GeoJson(
        selected_feature.to_json(),
        style_function=lambda feature: {"fillOpacity": 0, "color": "#6a3d9a", "weight": 5},
        control=False,
    ).add_to(camden_map)

    if show_candidates:
        candidates = tracts[pd.to_numeric(tracts["research_priority_rank"], errors="coerce") <= 5]
        candidate_group = folium.FeatureGroup(name="Top-five candidate tracts", overlay=True, control=True, show=True)
        folium.GeoJson(
            candidates.to_json(),
            style_function=lambda feature: {"fillOpacity": 0, "color": "#f4c842", "weight": 5, "dashArray": "9, 6"},
            control=False,
        ).add_to(candidate_group)
        candidate_group.add_to(camden_map)

    if show_services:
        service_group = MarkerCluster(name=f"Included service records ({len(services)}; verify operations)")
        for _, service in services.iterrows():
            latitude = pd.to_numeric(service.get("latitude"), errors="coerce")
            longitude = pd.to_numeric(service.get("longitude"), errors="coerce")
            if pd.isna(latitude) or pd.isna(longitude):
                continue
            folium.CircleMarker(
                [float(latitude), float(longitude)], radius=6, color="#fff", weight=2,
                fill=True, fill_color="#0b6e4f", fill_opacity=.95,
                tooltip=f"{safe(service.get('primary_name'))} — {safe(service.get('service_types'))}",
                popup=folium.Popup(service_popup(service), max_width=380),
            ).add_to(service_group)
        service_group.add_to(camden_map)

    if color_scale is not None:
        color_scale.add_to(camden_map)
    else:
        camden_map.get_root().html.add_child(folium.Element(
            "<div style='position:fixed;bottom:35px;left:45px;z-index:9999;background:white;padding:9px;border:1px solid #999'>"
            "<b>ML typology</b><br><span style='color:#d95f02'>■</span> Cluster 1<br>"
            "<span style='color:#159a84'>■</span> Cluster 2</div>"
        ))

    folium.LayerControl(collapsed=False).add_to(camden_map)
    Fullscreen(position="topleft", force_separate_button=True).add_to(camden_map)
    MeasureControl(position="topleft", primary_length_unit="miles", secondary_length_unit="kilometers").add_to(camden_map)
    camden_map.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])
    return camden_map


def render_dashboard():
    st.markdown(
        "### Where should an organization investigate providing additional food assistance?"
    )
    st.caption(
        "Choose a measure, explore Camden neighborhoods, select a neighborhood, and review what the evidence suggests should be verified next."
    )

    control1, control2, control3, control4 = st.columns([1.55, 1.55, .7, .7])
    selected_measure = control1.selectbox("1 · Choose evidence", list(MEASURES), key="dashboard_measure")
    selected_geoid = control2.selectbox(
        "2 · Choose a neighborhood",
        tracts["geoid"].tolist(),
        format_func=tract_label,
        key="dashboard_tract",
    )
    show_candidates = control3.toggle("Top-five outlines", value=True)
    show_services = control4.toggle("Service records", value=True)

    config = MEASURES[selected_measure]
    field = config["field"]
    selected_row = tracts.loc[tracts["geoid"] == selected_geoid].iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tracts assessed", len(tracts))
    m2.metric("Included service records", len(services))
    m3.metric("Candidate screen", "Top 5")
    m4.metric("ML typologies", tracts["ml_cluster"].nunique())

    map_column, insight_column = st.columns([2.2, 1], gap="medium")
    with map_column:
        camden_map = build_decision_map(
            selected_measure,
            selected_geoid,
            show_candidates,
            show_services,
        )

        st_folium(
            camden_map,
            key=f"map-{selected_measure}-{selected_geoid}-{show_candidates}-{show_services}",
            use_container_width=True,
            height=720,
            returned_objects=[],
        )
        st.caption(
            "Hover or click for neighborhood evidence. Green markers are included service records requiring verification; gold outlines show the top-five investigation screen; purple identifies the selected neighborhood."
        )

    with insight_column:
        st.subheader("3 · Interpret the evidence")
        st.markdown(f"**What this measure means**  \n{config['meaning']}")
        st.markdown(f"**How to read it**  \n{config['reading']}")

        if config.get("categorical", False):
            st.metric("Selected tract typology", f"Cluster {int(selected_row[field])}")
            st.markdown(f"**Profile:** {safe(selected_row.get('ml_typology'))}")
        else:
            series = pd.to_numeric(tracts[field], errors="coerce")
            selected_value = float(selected_row[field])
            median = float(series.median())
            comparison = "above" if selected_value > median else "below" if selected_value < median else "equal to"
            st.metric("Selected neighborhood", format_value(selected_value, config["format"]))
            st.metric("Camden tract median", format_value(median, config["format"]))
            st.markdown(
                f"**Comparison:** {safe(selected_row['neighborhood'])} is {comparison} the Camden tract median for this measure."
            )

        st.markdown(
            f"<div class='insight'><strong>Combined planning interpretation</strong><br>{planning_interpretation(selected_row)}</div>",
            unsafe_allow_html=True,
        )

        rank = int(selected_row["research_priority_rank"])
        if rank <= 5:
            next_step = "Verify nearby service operations and capacity, identify feasible community sites, and examine walking, transit and scheduling conditions."
        else:
            next_step = "Compare this neighborhood with the top-five candidates and determine whether local knowledge or unmeasured barriers justify further investigation."
        st.markdown(
            f"<div class='action'><strong>4 · Suggested next investigation</strong><br>{next_step}</div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class='caution'><strong>Interpret carefully.</strong> Results support prioritization and discussion; they do not measure confirmed unmet demand or select an operating site.</div>",
            unsafe_allow_html=True,
        )

    st.subheader("Five neighborhoods to investigate first")
    top_five = tracts.head(5).copy()
    top_five["Rank"] = top_five["research_priority_rank"].map(lambda value: f"#{int(value)}")
    top_five["Food insecurity"] = top_five["places_food_insecurity_pct"].map(lambda value: format_value(value, "percent"))
    top_five["Access ratio"] = top_five["relative_access_ratio"].map(lambda value: format_value(value, "ratio"))
    top_five["Gap units"] = top_five["relative_underserved_need_units"].map(lambda value: format_value(value, "number"))
    st.dataframe(
        top_five[["Rank", "neighborhood", "tract_name", "Food insecurity", "Access ratio", "Gap units"]].rename(
            columns={"neighborhood": "Neighborhood", "tract_name": "Census tract"}
        ),
        hide_index=True,
        use_container_width=True,
    )
    st.caption(
        "This is a modeled investigation screen—not a list of approved operating locations."
    )

    with st.expander("About the project and team"):
        st.markdown(
            """
            **Program:** Team 2 (Fall 2026 Cohort) Rutgers-Camden AI Campus AI/ML Cohort  
            **Team members:** Kristina Koot (PhD Student, Public Administration and Community Development), Anu J Khandelwal, Amisha Ratogi (Biology)  
            **Faculty, mentors or partners:** Ojobo Agbo Eje (MS,MBA).  
            **Research question:** Which Camden neighborhoods combine greater food-assistance need, weaker access to included services and larger relative service gaps-and would therefore warrant investigation for additional food-assistance?

            This prototype combines public data, spatial analysis and exploratory machine learning. AI supported code development, data review, documentation and interface design; the team remains responsible for validating methods, interpretations and outputs.

            Service operations, eligibility, schedules and capacity require direct verification. The platform does not represent an official Rutgers recommendation.
            """
        )


COMPARISON_MEASURES = [
    ("Need", "Food-insecurity prevalence", "places_food_insecurity_pct", "percent", "Higher suggests greater modeled prevalence."),
    ("Need", "Derived food-insecure adults", "estimated_food_insecure_adults", "integer", "A scale indicator derived from modeled prevalence and adult population."),
    ("Access", "Relative access ratio", "relative_access_ratio", "ratio", "Below 1 indicates access below the Camden benchmark."),
    ("Access", "Nearest included record", "nearest_service_miles", "miles", "Greater straight-line distance indicates weaker proximity."),
    ("Access", "Included records within one mile", "services_within_1mi", "integer", "Counts records, not confirmed capacity or availability."),
    ("Gap", "Potential relative gap units", "relative_underserved_need_units", "number", "Higher indicates a larger modeled relative gap."),
    ("Outreach", "Households without a vehicle", "acs_no_vehicle_households_pct", "percent", "Higher values may increase mobility barriers."),
    ("Outreach", "Adults with a disability", "places_disability_pct", "percent", "Higher values strengthen accessibility considerations."),
    ("Outreach", "Limited-English context", "acs_limited_english_pct", "percent", "Higher values support multilingual outreach."),
    ("Outreach", "Households without broadband", "no_broadband_subscription_pct", "percent", "Higher values caution against digital-only outreach."),
    ("Household context", "SNAP households with children", "snap_children_pct_all_households", "percent", "Percentage of all households; not a count of children."),
    ("Household context", "SNAP households with seniors", "snap_senior_pct_all_households", "percent", "Percentage of all households; not a count of seniors."),
]


def render_comparison():
    st.markdown("### Why do two neighborhoods differ?")
    st.caption(
        "Select two neighborhoods to compare need, modeled access, relative gaps and outreach context. Census-tract evidence is displayed under neighborhood names."
    )

    left_control, right_control = st.columns(2)
    left_geoid = left_control.selectbox(
        "Neighborhood A",
        tracts["geoid"].tolist(),
        index=0,
        format_func=tract_label,
        key="compare_left",
    )
    right_default = 1 if len(tracts) > 1 else 0
    right_geoid = right_control.selectbox(
        "Neighborhood B",
        tracts["geoid"].tolist(),
        index=right_default,
        format_func=tract_label,
        key="compare_right",
    )

    left = tracts.loc[tracts["geoid"] == left_geoid].iloc[0]
    right = tracts.loc[tracts["geoid"] == right_geoid].iloc[0]

    left_summary, right_summary = st.columns(2)
    for column, row in ((left_summary, left), (right_summary, right)):
        with column:
            st.markdown(f"#### {safe(row['neighborhood'])}")
            st.caption(f"{safe(row['tract_name'])} · Priority rank #{int(row['research_priority_rank'])}")
            c1, c2 = st.columns(2)
            c1.metric("Priority index", format_value(row["research_priority_index"], "number"))
            c2.metric("ML typology", f"Cluster {int(row['ml_cluster'])}")
            st.info(safe(row["ml_typology"]))

    rows = []
    for category, label, field, kind, note in COMPARISON_MEASURES:
        series = pd.to_numeric(tracts[field], errors="coerce")
        rows.append(
            {
                "Category": category,
                "Measure": label,
                safe(left["neighborhood"]): format_value(left[field], kind),
                "Camden tract median": format_value(series.median(), kind),
                safe(right["neighborhood"]): format_value(right[field], kind),
                "How to interpret": note,
            }
        )
    comparison = pd.DataFrame(rows)
    st.dataframe(comparison, hide_index=True, use_container_width=True)

    left_need = float(left["places_food_insecurity_pct"])
    right_need = float(right["places_food_insecurity_pct"])
    left_access = float(left["relative_access_ratio"])
    right_access = float(right["relative_access_ratio"])
    left_gap = float(left["relative_underserved_need_units"])
    right_gap = float(right["relative_underserved_need_units"])
    higher_need = left["neighborhood"] if left_need > right_need else right["neighborhood"] if right_need > left_need else "Neither neighborhood"
    weaker_access = left["neighborhood"] if left_access < right_access else right["neighborhood"] if right_access < left_access else "Neither neighborhood"
    larger_gap = left["neighborhood"] if left_gap > right_gap else right["neighborhood"] if right_gap > left_gap else "Neither neighborhood"

    st.markdown("#### Plain-language comparison")
    st.markdown(
        f"- **Greater modeled food-insecurity prevalence:** {safe(higher_need)}\n"
        f"- **Weaker modeled relative access:** {safe(weaker_access)}\n"
        f"- **Larger potential relative service gap:** {safe(larger_gap)}"
    )
    st.markdown(
        "<div class='action'><strong>How to use this comparison</strong><br>Use the differences to choose what to verify next: current service operations and capacity, feasible host sites, resident preferences, transportation conditions, schedules, eligibility and organizational fit. Do not select a site from the scores alone.</div>",
        unsafe_allow_html=True,
    )

    download = comparison.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download this comparison (CSV)",
        data=download,
        file_name=f"camden_comparison_{left_geoid}_{right_geoid}.csv",
        mime="text/csv",
    )


st.markdown('<div class="kicker">Rutgers–Camden AI Campus Urban Project</div>', unsafe_allow_html=True)
st.title("Camden Food Assistance Location Planning Platform")
st.markdown(
    '<div class="lede">A guided planning tool for exploring where food-assistance need, service access, outreach barriers and potential relative gaps intersect across Camden neighborhoods.</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="warning"><strong>Planning screen—not a final siting decision.</strong> Service operations, schedules, eligibility and capacity have not been independently confirmed.</div>',
    unsafe_allow_html=True,
)

dashboard_tab, comparison_tab = st.tabs(
    ["🏠 Decision Dashboard", "⚖️ Compare Neighborhoods"]
)

with dashboard_tab:
    render_dashboard()

with comparison_tab:
    render_comparison()

st.markdown("---")
st.caption(
    "Developed collaboratively by members of the Team 2 (Fall 2026 Cohort) as a decision-support prototype. Team: Kristina Koot (PhD Student, Public Administration and Community Development), Amisha Ratogi (Biology), Anu J Khandelwal. Mentor/AI Coach: Ojobo Agbo Eje (MS,MBA)."
)

