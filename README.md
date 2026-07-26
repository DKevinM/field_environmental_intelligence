# Field Environmental Intelligence

On-demand environmental conditions report for field workers — click a point on the map (or use your device location) and get a live report for that exact spot: weather, AQHI/PM2.5, nearby active fires, nearby road closures/incidents, active provincial alerts, and nearby traffic cameras.

Sibling project to [environmental_intelligence](https://github.com/DKevinM/environmental_intelligence) (the scheduled Calgary Folk Fest sit-rep), but architecturally different on purpose: that one is a batch job that regenerates a fixed venue's report on a cron schedule and publishes static HTML. This one is a live web service that computes a report for an arbitrary point at request time, aimed at someone deciding "is it safe to work here right now" rather than "what are conditions at this one fixed event."

Deliberately does **not** run the back-trajectory smoke-source model that the Calgary report uses — that answers a "where did this air come from" analytical question, not "is it safe here right now," and takes minutes to compute. This needs to respond in a couple of seconds.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export FIRMS_API_KEY=...    # see /opt/airquality/config/intelligence.env on the server
uvicorn main:app --host 0.0.0.0 --port 8811
```

Then open `http://localhost:8811/`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Notes

- `FIRMS_API_KEY` must be set as an environment variable — never commit it.
- AQHI/PM2.5 data is read from AB_datapull's local output files (`/opt/airquality/github/AB_datapull/...`), same source as the Calgary sit-rep.
- 511 Alberta endpoints (cameras, road events, weather stations, alerts) need no API key but are rate-limited to 10 calls/60s.
- Not yet exposed publicly — currently runs on localhost only. Making this reachable by actual field workers needs a decision on hosting/access (public port + auth vs. internal/VPN) before going further.
