# Field Environmental Intelligence

On-demand environmental conditions report for field workers — click a point on the map (or use your device location) and get a live report for that exact spot: weather, AQHI/PM2.5, nearby active fires, nearby road closures/incidents, active provincial alerts, and nearby traffic cameras.

Sibling project to [environmental_intelligence](https://github.com/DKevinM/environmental_intelligence) (the scheduled Calgary Folk Fest sit-rep), but architecturally different on purpose: that one is a batch job that regenerates a fixed venue's report on a cron schedule and publishes static HTML. This one is a live web service that computes a report for an arbitrary point at request time, aimed at someone deciding "is it safe to work here right now" rather than "what are conditions at this one fixed event."

Deliberately does **not** run the back-trajectory smoke-source model that the Calgary report uses — that answers a "where did this air come from" analytical question, not "is it safe here right now," and takes minutes to compute. This needs to respond in a couple of seconds.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo "FIRMS_API_KEY=..." > .env    # see /opt/airquality/config/intelligence.env on the server
uvicorn main:app --host 127.0.0.1 --port 8811
```

Then open `http://localhost:8811/`.

## Test

```bash
python -m unittest discover -s tests -v
```

## Notes

- `FIRMS_API_KEY` must be set as an environment variable (via `.env`, gitignored) — never commit it.
- AQHI/PM2.5 data is read from AB_datapull's local output files (`/opt/airquality/github/AB_datapull/...`), same source as the Calgary sit-rep.
- 511 Alberta endpoints (cameras, road events, weather stations, alerts) need no API key but are rate-limited to 10 calls/60s.
- No auth in front of `/report` yet — anyone with the URL can hit it. Fine for field-worker rollout for now, worth revisiting before wider use.

## Production setup (on this server)

The app runs as the `field-conditions` systemd service, bound to `127.0.0.1:8811` only — it is **not** reachable directly from the internet, no port is opened in any firewall. Public access goes through a **Cloudflare Tunnel** instead: the `cloudflared` systemd service holds an outbound-only connection to Cloudflare, which exposes it as `https://field.krmenvironmental.com` (tunnel `field-conditions`, config at `/etc/cloudflared/config.yml`). This was chosen over opening a port because it needs no inbound firewall rule at all — the server never accepts a connection from the public internet, only Cloudflare's edge relays to it outbound-initiated.

`docs/index.html` is a standalone copy of the map/click/geolocation page (identical to `templates/index.html`), hosted on **GitHub Pages** instead of served by this app, pointed at `BACKEND_URL = 'https://field.krmenvironmental.com'`. Reasoning: Pages gives free HTTPS, which the geolocation button needs to work on a phone. On click or "use my location" it does a plain full-page redirect to `BACKEND_URL + /report?lat=...&lon=...` — not a fetch, so no CORS issue.

To serve it: repo Settings → Pages → Source: Deploy from branch → `main` / `/docs`.

Both systemd services (`field-conditions`, `cloudflared`) are enabled and start on boot. Useful commands: `systemctl status field-conditions cloudflared`, `journalctl -u field-conditions -f`.
