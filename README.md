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

## Public map front-end (GitHub Pages)

`docs/index.html` is a standalone copy of the map/click/geolocation page (identical to `templates/index.html`) meant to be hosted on GitHub Pages instead of served by this app. Reasoning: Pages gives free HTTPS, which the geolocation button needs to work on a phone, without waiting on backend hosting. On click or "use my location" it does a plain full-page redirect to `BACKEND_URL + /report?lat=...&lon=...` — not a fetch, so no CORS/mixed-content issue even while the backend is plain HTTP.

To turn it on: repo Settings → Pages → Source: Deploy from branch → `main` / `/docs`.

Still open, in `docs/index.html`'s `BACKEND_URL` constant:
- Currently hardcoded to `http://207.126.161.96:8811` (this server's IP, the port `uvicorn` binds above). Update it if that changes.
- The app already binds `--host 0.0.0.0`, and there's no local firewall (ufw is inactive) blocking it — so reachability depends on the Kamatera cloud firewall/security group allowing inbound 8811, which hasn't been opened yet. The service also isn't currently running (nothing needs it while it's not public).
- No auth in front of `/report` yet — anyone with the URL can hit it. Fine for now, worth revisiting before wide rollout.
