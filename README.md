# camdenfoodcitingtool

# ============================================================
# PREPARE THE STREAMLIT PROJECT FOR GITHUB
# ============================================================

from pathlib import Path
import json
import pandas as pd
import geopandas as gpd

PROJECT_DIR = Path("/content/camden_streamlit")
DATA_DIR = PROJECT_DIR / "data"
STREAMLIT_DIR = PROJECT_DIR / ".streamlit"

STREAMLIT_DIR.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# requirements.txt
# ------------------------------------------------------------

requirements = """streamlit>=1.40,<2.0
streamlit-folium>=0.24,<1.0
folium>=0.19,<1.0
branca>=0.8,<1.0
pandas>=2.2,<3.0
geopandas>=1.0,<2.0
"""

(PROJECT_DIR / "requirements.txt").write_text(
    requirements,
    encoding="utf-8"
)


# ------------------------------------------------------------
# Streamlit configuration
# ------------------------------------------------------------

streamlit_config = """[theme]
primaryColor = "#CC0033"
backgroundColor = "#F5F3ED"
secondaryBackgroundColor = "#FFFFFF"
textColor = "#17231F"
font = "sans serif"

[server]
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
"""

(STREAMLIT_DIR / "config.toml").write_text(
    streamlit_config,
    encoding="utf-8"
)


# ------------------------------------------------------------
# .gitignore
# ------------------------------------------------------------

gitignore = """__pycache__/
*.py[cod]
.ipynb_checkpoints/
.streamlit/secrets.toml
.env
.DS_Store
"""

(PROJECT_DIR / ".gitignore").write_text(
    gitignore,
    encoding="utf-8"
)


# ------------------------------------------------------------
# README.md
# ------------------------------------------------------------

readme = """# Camden Food Assistance Location Planning Platform

An educational decision-support prototype developed collaboratively
through the Rutgers-Camden AI Campus AI/ML Cohort.

## Research question

Which Camden neighborhoods combine greater food-assistance need,
weaker access to included services and larger relative service gaps,
and would therefore warrant investigation for additional assistance?

## Platform sections

### Decision Dashboard

- Explore need, access, outreach and relative-gap measures.
- View included food-assistance service records.
- Examine the top-five investigation screen.
- Select a neighborhood and receive a plain-language interpretation.
- Identify evidence that should be verified next.

### Compare Neighborhoods

- Compare two Camden neighborhoods side by side.
- Review need, access, gap and outreach-context measures.
- Understand why their modeled priority positions differ.
- Download the comparison as a CSV file.

## Important limitations

This is a planning screen, not a final siting recommendation.

- Food insecurity and several other measures are modeled estimates.
- Included service records have not been independently confirmed for
  current operating status, eligibility, schedule or capacity.
- Distance measures are based on straight-line distance.
- The access model uses equal-capacity service proxies.
- Rankings do not represent observed unmet demand.
- Candidate tracts are not approved operating locations.
- Local verification and community engagement remain necessary.

## Project files

- `streamlit_app.py` — Streamlit application
- `data/camden_tracts.geojson` — Camden tract geometry and attributes
- `data/tract_master.csv` — tract-level analytical master table
- `data/service_locations.csv` — included service-location records
- `requirements.txt` — application dependencies
- `.streamlit/config.toml` — application appearance and configuration

## Run locally

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
