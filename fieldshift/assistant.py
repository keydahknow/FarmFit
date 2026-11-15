"""FarmFit assistant: a Gemini chat grounded in this farm's own data.

The model never sees raw secrets or personal data. It receives a compact,
factual briefing built from the same NASA / NOAA / FAO numbers the app
shows (climate, storm exposure, rotations, water status, active storms),
plus firm rules: stay on farming, say when data is uncertain, defer to
extension officers and official warnings, follow FDA flood food-safety
guidance, and answer in the farmer's language.
"""

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MODELS = ["gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"]

LANG_NAMES = {"en": "English", "es": "Spanish", "fr": "French", "ht": "Haitian Creole (Kreyòl ayisyen)"}

RULES = """You are FarmFit, a friendly farm adviser for small-scale farmers in the Caribbean and other
hurricane-prone regions. You are part of the "Hurricane to Harvest" app built for NASA Space Apps 2026.

How to answer:
- Use plain words a farmer with little technical training understands. Short paragraphs or a short list.
  Give concrete actions (what, when, how much) when you can.
- Ground answers in the FARM BRIEFING below. Quote its numbers when relevant (rain, months, storm odds,
  irrigation mm) and say which dataset they come from (e.g. "NASA POWER", "NOAA hurricane records").
- If the briefing does not contain the answer, say so and give general good practice, clearly marked as general.
- Be honest about uncertainty: satellite cells are larger than a farm; the storm model is an exposure screen,
  not a forecast. Never predict that a specific storm will or will not hit.
- For active storms, always point to the national met service and disaster office for official warnings
  (Jamaica: Meteorological Service and ODPEM; Trinidad and Tobago: TTMS and ODPM; elsewhere: the national service).
- Food safety: if floodwater touched the edible part of a crop, it should not be eaten or sold (U.S. FDA guidance);
  recommend checking with the Ministry of Agriculture extension officer.
- Pesticides and fertiliser: give general, label-following advice only; never give doses for restricted chemicals.
- Stay on farming, soil, water, weather, storms and the app. Politely decline unrelated requests.
- You support, never replace, the farmer's own judgment and local extension officers.
- Reply in {language}."""


def build_briefing(ctx):
    """ctx: dict of already-computed facts (strings / numbers). Returns compact text."""
    lines = ["FARM BRIEFING"]
    for title, body in ctx.items():
        if body in (None, "", [], {}):
            continue
        if isinstance(body, (list, tuple)):
            body = "\n".join(f"  - {b}" for b in body)
            lines.append(f"{title}:\n{body}")
        else:
            lines.append(f"{title}: {body}")
    return "\n".join(lines)


def ask(api_key, history, question, briefing, lang="en", model=None, timeout=60):
    """history: list of {"role": "user"|"assistant", "content": str}. Returns (text, info)."""
    if not api_key:
        return None, {"error": "No Gemini API key configured"}
    contents = []
    for turn in history[-12:]:
        contents.append({"role": "user" if turn["role"] == "user" else "model", "parts": [{"text": turn["content"]}]})
    contents.append({"role": "user", "parts": [{"text": question}]})
    body = {
        "system_instruction": {"parts": [{"text": RULES.format(language=LANG_NAMES.get(lang, "English")) + "\n\n" + briefing}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 900},
    }
    errors = []
    for name in ([model] if model else []) + [m for m in MODELS if m != model]:
        try:
            r = requests.post(GEMINI_URL.format(model=name), params={"key": api_key}, json=body, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
            if text:
                return text, {"model": name}
            errors.append(f"{name}: empty reply")
        except Exception as error:  # noqa: BLE001
            errors.append(f"{name}: {str(error)[:120]}")
    return None, {"error": " | ".join(errors)}


SUGGESTED = {
    "en": ["What should I plant before the next hurricane season?",
           "Is my farm drier than normal right now, and should I irrigate?",
           "A storm is coming in two days. What do I do with my crops?"],
    "es": ["¿Qué debo sembrar antes de la próxima temporada de huracanes?",
           "¿Mi finca está más seca de lo normal? ¿Debo regar?",
           "Viene una tormenta en dos días. ¿Qué hago con mis cultivos?"],
    "fr": ["Que dois-je planter avant la prochaine saison cyclonique ?",
           "Ma ferme est-elle plus sèche que d'habitude ? Dois-je irriguer ?",
           "Une tempête arrive dans deux jours. Que faire de mes cultures ?"],
    "ht": ["Kisa pou m plante anvan pwochen sezon siklòn nan?",
           "Èske jaden m nan pi sèk pase nòmal kounye a? Èske m dwe wouze?",
           "Gen yon tanpèt k ap vini nan de jou. Kisa pou m fè ak rekòt mwen yo?"],
}
