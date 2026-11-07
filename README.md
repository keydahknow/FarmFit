# FarmFit

FarmFit is a **Streamlit** web app that helps farmers explore crop choices using field location, crop data, water-demand screening, rotation logic, and guided recommendations.

Repository: [github.com/keydahknow/FarmFit](https://github.com/keydahknow/FarmFit)

## Features

- Map-based field pinning and location context
- Crop comparison and scoring from bundled datasets
- Water and intercropping reference data
- SQLite-backed app data (`farmfit.db`)

## Requirements

- Python 3.10+ (3.14 tested locally)
- Git (for team collaboration)

## Quick start

```powershell
git clone https://github.com/keydahknow/FarmFit.git
cd FarmFit
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### API keys (local only)

Some features need a **Gemini API key**. Create this file locally (it is **not** committed to Git):

`.streamlit/secrets.toml`

```toml
GEMINI_API_KEY = "your-key-here"
```

Never commit secrets. See [Streamlit secrets](https://docs.streamlit.io/develop/concepts/connections/secrets-management).

### Run the app

```powershell
streamlit run app.py
```

## Project layout

| File / folder | Purpose |
|---------------|---------|
| `app.py` | Main Streamlit application |
| `crops.csv`, `crop_water.csv`, `intercropping.csv` | Crop reference data |
| `farmfit.db` | SQLite database used by the app |
| `requirements.txt` | Python dependencies |
| `GIT_SHEET.md` | Git workflow guide for the team (on GitHub) |
| `GIT_SHEET.pdf` | Printable copy (generate locally with `scripts/md_to_pdf.py`) |
| `.streamlit/secrets.toml` | Local secrets (gitignored) |

## Working as a team

We use **branches** and **pull requests** on `main`. Read:

- [GIT_SHEET.md](GIT_SHEET.md) (editable on GitHub)

For a printable PDF, generate it locally (file stays on your machine, not in the repo):

```powershell
pip install markdown playwright
python -m playwright install chromium
python scripts/md_to_pdf.py
```

## Contributing

1. `git pull origin main`
2. Create a branch: `git checkout -b feature/short-name`
3. Commit with a clear message, push, open a pull request
4. Test with `streamlit run app.py` before merging

## License

Add a license file when the team chooses one (e.g. MIT).
