/*
  FarmFit soil probe: ground truth for NASA SMAP.

  Hardware (about US$10-15):
    - ESP32 dev board (e.g. ESP32-DevKitC)
    - Capacitive soil moisture sensor v1.2 (corrosion resistant; avoid resistive probes)
      VCC -> 3V3, GND -> GND, AOUT -> GPIO34 (ADC1, safe with Wi-Fi on)
    - Optional: 18650 cell + TP4056 charger + small solar panel; battery divider on GPIO35

  Every READ_EVERY_MIN minutes it wakes, takes 15 readings, uses the median,
  converts to 0-100 % relative wetness with a two-point calibration, and
  publishes JSON (IFRS sensor contract + soil fields) to an ntfy topic:

    {"device_id":"probe-01","ts":"2026-11-15T14:05:00Z","soil_raw":2310,"soil_pct":41.2,"battery_v":4.1,"seq":1043}

  The FarmFit "Water watch -> Ground truth" panel reads that topic live, or
  you can upload the CSV lines printed on Serial. It compares the pattern of
  your probe with SMAP and NASA POWER soil wetness.

  Calibrate once: note the raw value in dry air (DRY_RAW) and with the probe in
  a glass of water up to the line (WET_RAW). Insert the probe vertically in the
  root zone (5-10 cm), away from drip emitters.
*/

#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>

// ---- settings -------------------------------------------------------------
const char* WIFI_SSID     = "your-wifi";
const char* WIFI_PASSWORD = "your-password";
const char* DEVICE_ID     = "probe-01";
const char* NTFY_URL      = "https://ntfy.sh/farmfit-sensor-probe-01";   // pick your own topic name
const int   SOIL_PIN      = 34;
const int   BATT_PIN      = 35;      // set to -1 if no battery divider
const int   DRY_RAW       = 2900;    // reading in dry air
const int   WET_RAW       = 1300;    // reading in water
const int   READ_EVERY_MIN = 30;
// ---------------------------------------------------------------------------

RTC_DATA_ATTR uint32_t seq = 0;

int medianRead(int pin, int n) {
  int v[25];
  for (int i = 0; i < n; i++) { v[i] = analogRead(pin); delay(20); }
  for (int i = 1; i < n; i++) { int k = v[i], j = i - 1; while (j >= 0 && v[j] > k) { v[j + 1] = v[j]; j--; } v[j + 1] = k; }
  return v[n / 2];
}

float toPercent(int raw) {
  float pct = (float)(DRY_RAW - raw) / (float)(DRY_RAW - WET_RAW) * 100.0f;
  return pct < 0 ? 0 : (pct > 100 ? 100 : pct);
}

String isoNow() {
  struct tm t;
  if (!getLocalTime(&t, 5000)) return "";
  char buf[25];
  strftime(buf, sizeof(buf), "%Y-%m-%dT%H:%M:%SZ", &t);
  return String(buf);
}

void setup() {
  Serial.begin(115200);
  analogReadResolution(12);
  analogSetPinAttenuation(SOIL_PIN, ADC_11db);

  int raw = medianRead(SOIL_PIN, 15);
  float pct = toPercent(raw);
  float batt = BATT_PIN >= 0 ? analogReadMilliVolts(BATT_PIN) * 2 / 1000.0 : 0;   // 1:1 divider
  seq++;

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  for (int i = 0; i < 40 && WiFi.status() != WL_CONNECTED; i++) delay(250);
  configTime(0, 0, "pool.ntp.org", "time.google.com");
  String ts = isoNow();

  String json = String("{\"device_id\":\"") + DEVICE_ID + "\",\"ts\":\"" + ts + "\",\"soil_raw\":" + raw +
                ",\"soil_pct\":" + String(pct, 1) + ",\"battery_v\":" + String(batt, 2) + ",\"seq\":" + seq + "}";
  Serial.println("ts,soil_raw,soil_pct,battery_v");               // CSV header (ignored if repeated)
  Serial.printf("%s,%d,%.1f,%.2f\n", ts.c_str(), raw, pct, batt);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(NTFY_URL);
    http.addHeader("Title", "FarmFit soil probe");
    http.addHeader("Tags", "seedling");
    int code = http.POST(json);
    Serial.printf("published (%d): %s\n", code, json.c_str());
    http.end();
  }
  WiFi.disconnect(true);
  esp_sleep_enable_timer_wakeup((uint64_t)READ_EVERY_MIN * 60ULL * 1000000ULL);
  esp_deep_sleep_start();
}

void loop() {}
