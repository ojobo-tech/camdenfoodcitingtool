# Camden Food Assistance Location Planning Platform

A decision-support prototype developed collaboratively
through the Rutgers-Camden AI Campus AI/ML Cohort.
https://camdenfoodassistancetool.streamlit.app/

## Research question

Which Camden neighborhoods combine greater food-assistance need,
weaker access to included services and larger relative service gaps,
and would therefore warrant investigation for additional assistance?

## Decision Dashboard

The dashboard (https://camdenfoodassistancetool.streamlit.app/) allows users to:

- Explore need, access, outreach and relative-gap measures.
- View included food-assistance service records.
- Examine the top-five investigation screen.
- Select a neighborhood and receive a plain-language interpretation.
- Identify evidence that should be verified next.

## Compare Neighborhoods

The comparison section allows users to:

- Compare two Camden neighborhoods.
- Review need, access, gap and outreach-context measures.
- Understand why modeled priority positions differ.
- Download a comparison as a CSV file.

## Important limitations

This is a planning screen, not a final siting recommendation.

- Food insecurity and several other measures are modeled estimates.
- Service records have not been independently confirmed for current
  operating status, eligibility, schedule or capacity.
- Distance measures use straight-line distance.
- The access model uses equal-capacity service proxies.
- Rankings do not represent observed unmet demand.
- Candidate tracts are not approved operating locations.
- Local verification and community engagement remain necessary.

## Project files

- streamlit_app.py: Streamlit application
- data/camden_tracts.geojson: Camden tract geometry and attributes
- data/tract_master.csv: tract-level analytical master table
- data/service_locations.csv: included service-location records
- requirements.txt: application dependencies
- .streamlit/config.toml: application configuration

## Running the application

Install the requirements:

python -m pip install -r requirements.txt

Run Streamlit:

python -m streamlit run streamlit_app.py

## Team acknowledgment

Developed collaboratively by members of the Rutgers-Camden AI Campus
AI/ML Cohort as an educational decision-support prototype.

Before public release, add:

- Confirmed team-member names and roles
- Faculty, mentors and project partners
- Repository contact
- Project contact
- Final data-source citations
- Prototype version and release date

## AI-use disclosure

AI supported code development, data review, documentation and
interface design. The project team remains responsible for validating
the methods, data, interpretations and published outputs.

## Non-endorsement statement

This prototype does not represent an official Rutgers recommendation
or final food-assistance siting decision unless separately authorized.
