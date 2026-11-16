# Connecting Google Gemini to FarmFit

FarmFit is a **Python Streamlit app**. All Gemini calls happen on the server, in Python, so the key never reaches the farmer's browser, the page source or the GitHub repository.

## Where Gemini is used

| Feature | Code | What Gemini does | What it never does |
|---|---|---|---|
| **Ask FarmFit** (News & ask page) | `fieldshift/assistant.py` → `ask()` | Answers farmer questions in English, Spanish, French or Kreyòl, using a briefing built from this farm's data: climate, storms, soil, plans, satellite water status, El Niño outlook | It is told to stay on farming, use only the briefing's numbers, and point to ODPM / ODPEM and extension officers for emergencies |
| **After a storm: field photo check** | `fieldshift/recovery.py` → `assess_photo()` | Describes what is *visible* in a field photo (standing water, flattened crops, debris) as JSON with a confidence value | It never decides recovery stages: documented rules plus farmer confirmation do |
| **Pest & disease watch: photo suggestion** | `fieldshift/community.py` → `ai_triage()` | Suggests a category and a likely pest or disease, with a confidence value | It never sets a report's category or status; reports stay *Unverified* until an officer reviews them |

All three use the REST endpoint `https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`. They try `gemini-2.5-flash` first, then `gemini-flash-latest` and `gemini-2.0-flash`, so a retired model name doesn't break the app.

## 1. Get a key

1. Go to **https://aistudio.google.com** and sign in with a Google account.
2. Click **Get API key → Create API key**, choose or create a Google Cloud project, and copy the key.
3. The free tier is enough for a demo. For production, set a usage limit in Google Cloud.

## 2. Store it securely

The app reads secrets with `ui.secret(name)`: first from Streamlit secrets, then from environment variables.

**Running on your computer:** create `.streamlit/secrets.toml` in the project folder. This file is listed in `.gitignore` and must never be committed.

```toml
GEMINI_API_KEY = "paste-your-key-here"
# optional
GEMINI_MODEL = "gemini-2.5-flash"
AUTHORITY_PASSCODE = "a-long-passcode-for-agricultural-officers"
EARTHDATA_USERNAME = "your-earthdata-username"
EARTHDATA_PASSWORD = "your-earthdata-password"
```

Restart Streamlit after saving the file (Ctrl + C, then `streamlit run app.py`).

**Instead, with environment variables** (e.g. Docker or a server):

```bash
export GEMINI_API_KEY="paste-your-key-here"
streamlit run app.py
```

**On Streamlit Community Cloud:** open the app, then **⋮ → Settings → Secrets**. Paste the same TOML lines and save; the app restarts on its own.

**GitHub Actions** (the scheduled data refresh) does **not** need the Gemini key. Only the Earthdata secrets go under **Settings → Secrets and variables → Actions**.

Never paste the key into a chat, an issue, a commit, a screenshot or front-end code.

## 3. Check it works

- **News & ask** page: click a suggested question. The answer should quote this farm's numbers.
- **Storms & recovery → Respond & recover:** upload a field photo and press the assessment button.
- **Pest watch → Report a problem:** upload a leaf photo and press **Ask AI what it might be**. You get a suggestion with a confidence value, marked "not a diagnosis".

If the key is missing, each feature says so and the rest of the app works normally.

## 4. How the backend call looks

```python
from fieldshift import assistant, ui

key = ui.secret("GEMINI_API_KEY")          # server side only
answer, info = assistant.ask(key, history=[], question="Should I plant tomatoes this month?",
                             briefing=assistant.build_briefing(context), lang="en")
```

`assistant.build_briefing()` turns the farm's computed data (monthly climate, storm exposure, soil, the current plan, SMAP and MODIS status, the ENSO outlook) into plain text. Gemini is told to answer only from that text. This keeps the AI grounded in measured data instead of general guesses.

## 5. Image analysis for pests and diseases

`community.ai_triage(image_bytes, mime_type, api_key)` sends the photo inline (base64) with a prompt that asks for JSON: `category`, `likely`, `confidence`, `visible` and `next_step`. The app:

- shows the result as **"AI suggestion, not a diagnosis"** with its confidence;
- pre-selects the category but lets the farmer change it;
- stores the suggestion with the report so an officer can see it, but leaves the report **Unverified**;
- re-encodes photos before saving, which strips EXIF data, including GPS location.

## Privacy and safety

- Gemini receives the photo or the question plus the farm briefing. The briefing gives the location only to one decimal place (about 11 km), never the exact field.
- Pest reports store a location blurred to the centre of a ~2 km grid square.
- Officer review needs `AUTHORITY_PASSCODE`. A real deployment would replace this with proper accounts for ministry staff.
