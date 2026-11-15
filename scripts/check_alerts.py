"""Check every watched farm for storm / drought alerts and send new ones.

Run by .github/workflows/storm-alerts.yml (every 3 hours in hurricane
season, daily otherwise). Already-sent alerts are remembered in
data/cache/alerts_state.json (no personal data), so farmers get one
message per storm level and one per dry or wet month.
"""

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fieldshift import alerts, power, stormwatch  # noqa: E402

STATE = power.CACHE_DIR / "alerts_state.json"


def main():
    farms = json.loads((ROOT / "data" / "farms.json").read_text())["farms"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    active, err = stormwatch.active_storms()
    if err:
        print("NHC feed:", err)
    sent = 0
    for f in farms:
        record, _ = power.fetch_daily(f["lat"], f["lon"], allow_network=False)
        recent, _ = power.fetch_window(f["lat"], f["lon"], end_date=date.today(), days=75)
        topic = alerts.topic_for(f["id"], f["lat"], f["lon"], f.get("label"))
        for a in alerts.evaluate(f["lat"], f["lon"], f.get("label", f["id"]), active or [], record, recent):
            key = f"{f['id']}|{a['key']}"
            if key in state:
                continue
            try:
                alerts.send_ntfy(topic, a)
                n = alerts.send_sms(alerts.sms_numbers(f["id"]), a)
                state[key] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                sent += 1
                print(f"sent  {topic}: {a['title']} (+{n} SMS)")
            except Exception as error:  # noqa: BLE001
                print(f"FAILED {topic}: {a['title']}: {error}")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(dict(sorted(state.items())[-500:]), indent=1))
    print(f"{sent} new alert(s).")


if __name__ == "__main__":
    main()
