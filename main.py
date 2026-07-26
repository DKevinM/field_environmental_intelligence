from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from modules.weather.service import load_weather
from modules.air_quality.service import load_current_aqhi,load_forecast_aqhi,load_nearest_pollutant,load_nearest_purpleair,load_blend_estimate
from modules.fire.service import load_hotspots
from modules.roads.service import load_nearby_events,load_nearby_weatherstations,load_active_alerts
from modules.roads.cameras import load_nearby_cameras
from modules.alerts.service import load_weather_alerts
from modules.intelligence import map_layers
from modules.intelligence.hazard_engine import assess
from modules.intelligence.narrative import build as build_narrative
from modules.intelligence.report import build_html
TZ='America/Edmonton'
INDEX_HTML=(Path(__file__).parent/'templates'/'index.html').read_text(encoding='utf-8')
app=FastAPI(title='Field Conditions Report')
@app.get('/',response_class=HTMLResponse)
def index():
    return INDEX_HTML
@app.get('/report',response_class=HTMLResponse)
def report(lat:float=Query(...,ge=-90,le=90),lon:float=Query(...,ge=-180,le=180)):
    w=load_weather(lat,lon,TZ)
    aq=load_current_aqhi(lat,lon)
    fx=load_forecast_aqhi(lat,lon)
    aq['pollutant']=load_nearest_pollutant(lat,lon)
    aq['purpleair']=load_nearest_purpleair(lat,lon)
    aq['blend']=load_blend_estimate(lat,lon)
    fire=load_hotspots(lat,lon)
    events=load_nearby_events(lat,lon)
    ws=load_nearby_weatherstations(lat,lon)
    alerts=load_active_alerts()
    wx_alerts=load_weather_alerts(lat,lon)
    cameras=load_nearby_cameras(lat,lon)
    mp=map_layers.build(lat,lon)
    a=assess(w,aq,fx,TZ)
    n=build_narrative(w,aq,fx,a,fire,events,alerts,ws.get('nearest') if ws.get('status')=='ok' else None,wx_alerts)
    now=datetime.now(ZoneInfo(TZ)).isoformat(timespec='seconds')
    return build_html(lat,lon,now,TZ,w,aq,fx,a,n,fire,cameras,events,alerts,wx_alerts,mp)
