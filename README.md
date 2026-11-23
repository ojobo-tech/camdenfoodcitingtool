

## Camden Food Assistance Location Planning Platform

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
