import json
from html import escape
from core.timefmt import format_long,tz_abbrev
from core.aqhi import cap as cap_aqhi
from core.geometry import compass
from modules.weather.codes import label as weather_label
R={'LOW':'low','MODERATE':'moderate','HIGH':'high','EXTREME':'extreme','UNKNOWN':'unknown'}
def v(x,s=''):return '—' if x is None else f'{x}{s}'
MAP_JS='''(function(){
  var map=L.map('fieldmap',{scrollWheelZoom:false}).setView([POINT.lat,POINT.lon],12);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OpenStreetMap contributors &copy; CARTO',maxZoom:19}).addTo(map);
  var pointMarker=L.circleMarker([POINT.lat,POINT.lon],{radius:10,color:'#fff',weight:3,fillColor:'#4dabf7',fillOpacity:1}).bindPopup('<b>Job location</b>').addTo(map);
  var fireLayer=L.layerGroup(FIRE.map(function(f){return L.circleMarker([f.lat,f.lon],{radius:7,color:'#fff',weight:1,fillColor:'#ff6b35',fillOpacity:0.9}).bindPopup('Active fire (NASA FIRMS)<br>'+f.distance_km+' km '+f.direction);}));
  var camLayer=L.layerGroup(CAMERAS.map(function(c){return L.circleMarker([c.lat,c.lon],{radius:6,color:'#fff',weight:1,fillColor:'#48cae4',fillOpacity:0.9}).bindPopup('<b>'+c.name+'</b><br>'+c.distance_km+' km '+c.direction);}));
  var eventLayer=L.layerGroup(EVENTS.map(function(e){return L.circleMarker([e.lat,e.lon],{radius:7,color:'#fff',weight:1,fillColor:e.is_full_closure?'#c92a2a':'#e0a800',fillOpacity:0.9}).bindPopup('<b>'+(e.roadway||'Road event')+'</b><br>'+(e.description||'')+'<br>'+e.distance_km+' km '+e.direction);}));
  fireLayer.addTo(map);camLayer.addTo(map);eventLayer.addTo(map);
  L.control.layers(null,{'Active fires':fireLayer,'Traffic cameras':camLayer,'Road events':eventLayer},{collapsed:false}).addTo(map);
})();'''
def build_map_section(lat,lon,fire,cameras,events):
 hotspots=(fire or {}).get('hotspots') or []
 fire_pts=[{'lat':hh['lat'],'lon':hh['lon'],'distance_km':hh['distance_km'],'direction':hh['direction']} for hh in hotspots]
 cam_pts=[{'lat':cc['lat'],'lon':cc['lon'],'name':cc.get('name'),'distance_km':cc.get('distance_km'),'direction':cc.get('direction')} for cc in (cameras or {}).get('cameras',[]) if cc.get('lat') is not None]
 ev_pts=[{'lat':e['lat'],'lon':e['lon'],'roadway':e.get('roadway'),'description':e.get('description'),'is_full_closure':e.get('is_full_closure'),'distance_km':e.get('distance_km'),'direction':e.get('direction')} for e in (events or {}).get('events',[]) if e.get('lat') is not None]
 point={'lat':lat,'lon':lon}
 data_js=(f"const POINT={json.dumps(point)};\nconst FIRE={json.dumps(fire_pts)};\nconst CAMERAS={json.dumps(cam_pts)};\nconst EVENTS={json.dumps(ev_pts)};\n")
 return f'<section class="panel"><h2>Local area map</h2><div id="fieldmap" style="height:420px;border-radius:12px;overflow:hidden"></div><script>{data_js}{MAP_JS}</script></section>'
def build_html(lat,lon,generated_at,tz,w,aq,fx,a,n,fire,cameras,events,alerts,wx_alerts=None):
 c=w.get('current',{})
 wx=(wx_alerts or {}).get('alerts') or []
 wx_section=('<section class="panel" style="border-color:#e8590c"><h2>Active Environment Canada alerts</h2>'+''.join(f"<article style='margin-bottom:12px'><b>{escape(x.get('name') or '').title()}</b> — {escape(x.get('region') or '')}<div style='white-space:pre-wrap;font-size:14px;color:#c9d4de;margin-top:6px'>{escape((x.get('text') or '')[:600])}{'…' if len(x.get('text') or '')>600 else ''}</div></article>" for x in wx)+'</section>') if wx else ''
 cards=''.join(f"<article class='hazard {R.get(x['risk'],'unknown')}'><small>{k.replace('_',' ').title()}</small><b>{x['risk']}</b><span>{v(cap_aqhi(x.get('indicator')) if k=='air_quality' else x.get('indicator'))} {x.get('unit','')}</span></article>" for k,x in a['hazards'].items())
 rec=''.join(f'<li>{escape(x)}</li>' for x in n['recommendations'])
 cams=(cameras or {}).get('cameras',[])
 cam_cards=''.join(f"<figure style='margin:0'><img data-src='{escape(cc['image_url'])}' class='livecam' alt='{escape(cc['name'])}' style='width:100%;border-radius:8px;display:block;background:#111c26'><figcaption style='font-size:13px;color:#9fb0bf;margin-top:6px'>{escape(cc['name'])} · {cc['distance_km']} km {escape(cc['direction'])}</figcaption></figure>" for cc in cams)
 cam_section=f'<section class="panel"><h2>Nearby traffic cameras</h2><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">{cam_cards}</div><script>document.querySelectorAll("img.livecam").forEach(function(img){{img.src=img.dataset.src+(img.dataset.src.indexOf("?")>-1?"&":"?")+"t="+Date.now();}});</script></section>' if cam_cards else ''
 ev_rows=''.join(f"<tr><td>{escape(str(e.get('roadway') or '—'))}</td><td>{escape(str(e.get('description') or ''))[:80]}</td><td>{'Full closure' if e.get('is_full_closure') else (e.get('event_type') or '—')}</td><td>{v(e.get('distance_km'),' km')} {escape(str(e.get('direction') or ''))}</td></tr>" for e in (events or {}).get('events',[])[:10])
 ev_section=f'<section class="panel"><h2>Road events near this location</h2><div style="overflow:auto"><table><tr><th>Roadway</th><th>Description</th><th>Type</th><th>Distance</th></tr>{ev_rows}</table></div></section>' if ev_rows else ''
 map_section=build_map_section(lat,lon,fire,cameras,events)
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Field Conditions Report</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{{margin:0;background:#0f1720;color:#f4f7fa;font-family:Arial}}header,main,footer{{max-width:1100px;margin:auto;padding:20px}}.panel,.metric,.hazard{{background:#172330;border:1px solid #304152;border-radius:12px;padding:16px}}.grid{{display:grid;gap:12px}}.metrics{{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}}.hazards{{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}}.hazard b,.metric b{{display:block;font-size:25px;margin:8px 0}}.low{{border-color:#2f9e44}}.moderate{{border-color:#e0a800}}.high{{border-color:#e8590c}}.extreme{{border-color:#c92a2a}}.unknown{{border-color:#6c757d}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #304152;text-align:left}}section{{margin-bottom:15px}}.leaflet-container{{background:#111c26}}</style></head><body><header><h1>Field Conditions Report</h1><p>{v(lat)}, {v(lon)} · Generated {escape(format_long(generated_at,tz))}</p><p><a href="/" style="color:#4dabf7">&larr; check a different location</a></p></header><main>{wx_section}<section class="panel"><h2>Overall risk: {a['overall_risk']}</h2></section><section class="grid metrics"><div class="metric">Temperature<b>{v(c.get('temperature_c'),'°C')}</b></div><div class="metric">Feels like<b>{v(c.get('apparent_temperature_c'),'°C')}</b></div><div class="metric">Wind<b>{v(c.get('wind_speed_kmh'),' km/h')}</b><small>from {escape(compass(c.get('wind_direction_deg')))}</small></div><div class="metric">Current AQHI<b>{v(cap_aqhi(aq.get('aqhi')))}</b><small>{escape(str(aq.get('station_name','Unavailable')))}</small></div></section><section class="panel"><h2>Hazard assessment</h2><div class="grid hazards">{cards}</div></section><section class="panel"><h2>Summary</h2><p>{escape(n['summary'])}</p><h3>Recommendations</h3><ul>{rec}</ul></section>{map_section}{ev_section}{cam_section}</main><footer>Live on-demand report — not a scheduled/cached page. Confirm official warnings before field work in hazardous conditions.</footer></body></html>'''
