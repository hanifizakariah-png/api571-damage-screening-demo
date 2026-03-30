# API 571 Damage Mechanism Screening Demo

Local Streamlit MVP that screens likely API 571 style damage mechanisms using
simplified deterministic engineering rules.

## What this demo does

- Loads a mock dataset of equipment items and corrosion loops.
- Supports CSV and Excel upload workflows for user data.
- Reads the first worksheet automatically for Excel uploads.
- Provides a simple column mapping step before screening.
- Adds a row-level data quality layer before running the rules.
- Screens 8 simplified damage mechanisms with transparent rule logic.
- Adds a backend knowledge-base library for the 8 damage mechanisms.
- Uses a deterministic Kahneman-inspired two-stage reasoning pattern:
  fast text-context cueing plus slower structured knowledge-base validation.
- Returns a score, triggered conditions, and a short engineering explanation.
- Adds qualitative confidence labels based on rule completeness and data quality.
- Exports screening results to Excel with original data, mapped data, quality status,
  top mechanisms, explanations, and assumptions used.
- Shows row-level input gaps so missing data is visible during screening.
- Flags rows with missing critical data as `Insufficient data`.
- Uses `Needs engineer review` where partial indicators are present but the
  rule threshold is not fully met.

## Included damage mechanisms

- CUI
- Chloride SCC
- Wet H2S damage / SSC risk
- CO2 corrosion
- Amine corrosion
- Sulfidation
- Caustic cracking
- Erosion-corrosion

## Project structure

```text
.
|-- app.py
|-- data/
|   `-- sample_input.csv
|-- screening/
|   |-- __init__.py
|   |-- data_loader.py
|   |-- data_quality.py
|   |-- engine.py
|   `-- rules.json
|-- requirements.txt
`-- README.md
```

## How to run locally

1. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

2. Activate it:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Launch Streamlit:

   ```powershell
   streamlit run app.py
   ```

5. Open the local URL shown in the terminal, usually:

   ```text
   http://localhost:8501
   ```

## Notes

- This is a deterministic demo, not a validated RBI or fitness-for-service tool.
- The rules are intentionally simplified and stored in
  `screening/rules.json` so they can be modified easily later.
- The sample dataset is in `data/sample_input.csv`.
- The app can generate a sample Excel template with a sample input sheet and a
  data dictionary sheet.
- Uploaded datasets must be mapped to the expected fields before screening.
