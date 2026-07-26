import json
from html import escape
from core.timefmt import format_long,format_short,tz_abbrev
from core.aqhi import cap as cap_aqhi
from core.geometry import compass
from modules.weather.codes import label as weather_label
R={'LOW':'low','MODERATE':'moderate','HIGH':'high','EXTREME':'extreme','UNKNOWN':'unknown'}
def v(x,s=''):return '—' if x is None else f'{x}{s}'
MAP_JS='''(function(){
  var map=L.map('fieldmap',{scrollWheelZoom:false}).setView([POINT.lat,POINT.lon],12);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',{attribution:'&copy; OpenStreetMap contributors &copy; CARTO',maxZoom:19}).addTo(map);
  function colorForPM25(x){if(x==null)return '#6c757d';if(x<12)return '#2f9e44';if(x<35.4)return '#e0a800';if(x<55.4)return '#e8590c';if(x<150.4)return '#c92a2a';if(x<250.4)return '#862e9c';return '#5c0000';}
  function colorForAQHI(x){if(x==null)return '#6c757d';if(x<=3)return '#2f9e44';if(x<=6)return '#e0a800';if(x<=10)return '#e8590c';return '#c92a2a';}
  function capAQHI(x){if(x==null)return 'n/a';var n=(typeof x==='number')?x:parseFloat(x);return (!isNaN(n)&&n>10)?'10+':x;}
  var pointMarker=L.circleMarker([POINT.lat,POINT.lon],{radius:10,color:'#fff',weight:3,fillColor:'#4dabf7',fillOpacity:1}).bindPopup('<b>Job location</b>').addTo(map);
  var aqhiLayer=L.geoJSON(AQHI_GRID,{style:function(f){return {fillColor:f.properties.color||'#6c757d',color:'transparent',fillOpacity:0.35};},onEachFeature:function(f,l){l.bindPopup('AQHI '+capAQHI(f.properties.value)+' &middot; confidence '+(f.properties.confidence||'unknown'));}});
  var smokeLayer=L.geoJSON(FIRESMOKE,{style:function(f){return {fillColor:colorForPM25(f.properties.pm25),color:'transparent',fillOpacity:0.35};},onEachFeature:function(f,l){var pv=f.properties.pm25;l.bindPopup('Smoke PM2.5 ~'+(pv!=null?pv.toFixed(1):'n/a')+' &micro;g/m&sup3;');}});
  var paLayer=L.layerGroup(PURPLEAIR.map(function(p){return L.circleMarker([p.lat,p.lon],{radius:6,color:'#fff',weight:1,fillColor:colorForPM25(p.pm25),fillOpacity:0.9}).bindPopup('<b>'+p.name+'</b><br>PM2.5: '+(p.pm25!=null?p.pm25:'n/a')+' &micro;g/m&sup3;<br>'+p.distance_km+' km away');}));
  var stationLayer=L.layerGroup(STATIONS.map(function(s){return L.circleMarker([s.lat,s.lon],{radius:8,color:'#fff',weight:2,fillColor:colorForAQHI(s.aqhi),fillOpacity:0.95}).bindPopup('<b>'+s.name+'</b><br>AQHI now: '+capAQHI(s.aqhi)+'<br>+3h: '+capAQHI(s.aqhi_3h!=null?+s.aqhi_3h.toFixed(1):null)+'<br>'+s.distance_km+' km away');}));
  var fireLayer=L.layerGroup(FIRE.map(function(f){return L.circleMarker([f.lat,f.lon],{radius:7,color:'#fff',weight:1,fillColor:'#ff6b35',fillOpacity:0.9}).bindPopup('Active fire (NASA FIRMS)<br>'+f.distance_km+' km '+f.direction);}));
  var camLayer=L.layerGroup(CAMERAS.map(function(c){return L.circleMarker([c.lat,c.lon],{radius:6,color:'#fff',weight:1,fillColor:'#48cae4',fillOpacity:0.9}).bindPopup('<b>'+c.name+'</b><br>'+c.distance_km+' km '+c.direction);}));
  var eventLayer=L.layerGroup(EVENTS.map(function(e){return L.circleMarker([e.lat,e.lon],{radius:7,color:'#fff',weight:1,fillColor:e.is_full_closure?'#c92a2a':'#e0a800',fillOpacity:0.9}).bindPopup('<b>'+(e.roadway||'Road event')+'</b><br>'+(e.description||'')+'<br>'+e.distance_km+' km '+e.direction);}));
  aqhiLayer.addTo(map);smokeLayer.addTo(map);paLayer.addTo(map);stationLayer.addTo(map);fireLayer.addTo(map);camLayer.addTo(map);eventLayer.addTo(map);
  L.control.layers(null,{'AQHI grid':aqhiLayer,'Smoke (PM2.5 model)':smokeLayer,'Community sensors':paLayer,'Official stations':stationLayer,'Active fires':fireLayer,'Traffic cameras':camLayer,'Road events':eventLayer},{collapsed:false}).addTo(map);
})();'''
def build_map_section(lat,lon,fire,cameras,events,mp=None):
 mp=mp or {}
 hotspots=(fire or {}).get('hotspots') or []
 fire_pts=[{'lat':hh['lat'],'lon':hh['lon'],'distance_km':hh['distance_km'],'direction':hh['direction']} for hh in hotspots]
 cam_pts=[{'lat':cc['lat'],'lon':cc['lon'],'name':cc.get('name'),'distance_km':cc.get('distance_km'),'direction':cc.get('direction')} for cc in (cameras or {}).get('cameras',[]) if cc.get('lat') is not None]
 ev_pts=[{'lat':e['lat'],'lon':e['lon'],'roadway':e.get('roadway'),'description':e.get('description'),'is_full_closure':e.get('is_full_closure'),'distance_km':e.get('distance_km'),'direction':e.get('direction')} for e in (events or {}).get('events',[]) if e.get('lat') is not None]
 aqhi_grid=mp.get('aqhi_grid') or {'type':'FeatureCollection','features':[]}
 firesmoke=mp.get('firesmoke') or {'type':'FeatureCollection','features':[]}
 purpleair=mp.get('purpleair') or []
 stations=mp.get('stations') or []
 point={'lat':lat,'lon':lon}
 data_js=(f"const POINT={json.dumps(point)};\nconst FIRE={json.dumps(fire_pts)};\nconst CAMERAS={json.dumps(cam_pts)};\nconst EVENTS={json.dumps(ev_pts)};\nconst AQHI_GRID={json.dumps(aqhi_grid)};\nconst FIRESMOKE={json.dumps(firesmoke)};\nconst PURPLEAIR={json.dumps(purpleair)};\nconst STATIONS={json.dumps(stations)};\n")
 return f'<section class="panel"><h2>Local area map</h2><div id="fieldmap" style="height:420px;border-radius:12px;overflow:hidden"></div><script>{data_js}{MAP_JS}</script></section>'
def build_html(lat,lon,generated_at,tz,w,aq,fx,a,n,fire,cameras,events,alerts,wx_alerts=None,mp=None):
 c=w.get('current',{})
 wx_status=(wx_alerts or {}).get('status')
 wx=(wx_alerts or {}).get('alerts') or []
 if wx:
  wx_section=('<section class="panel" style="border-color:#e8590c"><h2>Active Environment Canada alerts</h2>'+''.join(f"<article style='margin-bottom:12px'><b>{escape(x.get('name') or '').title()}</b> — {escape(x.get('region') or '')}<div style='white-space:pre-wrap;font-size:14px;color:#c9d4de;margin-top:6px'>{escape((x.get('text') or '')[:600])}{'…' if len(x.get('text') or '')>600 else ''}</div></article>" for x in wx)+'</section>')
 elif wx_status=='ok':
  wx_section='<section class="panel" style="border-color:#2f9e44"><p style="margin:0">✓ No active Environment Canada weather alerts for this location.</p></section>'
 else:
  wx_section=f'<section class="panel" style="border-color:#e0a800"><p style="margin:0">⚠ Could not retrieve Environment Canada weather alerts for this location{" (" + escape(str((wx_alerts or {}).get("error"))) + ")" if (wx_alerts or {}).get("error") else ""} — check manually before relying on this report.</p></section>'
 bulletins=(alerts or {}).get('alerts') or []
 bulletin_section=('<section class="panel" style="border-color:#e0a800"><h2>Provincial travel bulletins (511 Alberta)</h2><p style="font-size:13px;color:#9fb0bf;margin-top:0">Province-wide, not filtered to this specific location — confirm relevance before acting on it.</p>'+''.join(f"<article style='margin-bottom:12px'><b>{escape(x.get('message') or '')}</b><div style='font-size:14px;color:#c9d4de;margin-top:6px'>{escape(x.get('notes') or '')}</div></article>" for x in bulletins)+'</section>') if bulletins else ''
 cards=''.join(f"<article class='hazard {R.get(x['risk'],'unknown')}'><small>{k.replace('_',' ').title()}</small><b>{x['risk']}</b><span>{v(cap_aqhi(x.get('indicator')) if k=='air_quality' else x.get('indicator'))} {x.get('unit','')}</span></article>" for k,x in a['hazards'].items())
 rec=''.join(f'<li>{escape(x)}</li>' for x in n['recommendations'])
 summary_bullets=''.join(f'<li>{escape(x)}</li>' for x in n.get('summary_points') or [n['summary']])
 cams=(cameras or {}).get('cameras',[])
 cam_cards=''.join(f"<figure style='margin:0'><img data-src='{escape(cc['image_url'])}' class='livecam' alt='{escape(cc['name'])}' style='width:100%;border-radius:8px;display:block;background:#111c26'><figcaption style='font-size:13px;color:#9fb0bf;margin-top:6px'>{escape(cc['name'])} · {cc['distance_km']} km {escape(cc['direction'])}</figcaption></figure>" for cc in cams)
 cam_section=f'<section class="panel"><h2>Nearby traffic cameras</h2><div class="grid" style="grid-template-columns:repeat(auto-fit,minmax(220px,1fr))">{cam_cards}</div><script>document.querySelectorAll("img.livecam").forEach(function(img){{img.src=img.dataset.src+(img.dataset.src.indexOf("?")>-1?"&":"?")+"t="+Date.now();}});</script></section>' if cam_cards else ''
 ev_rows=''.join(f"<tr><td>{escape(str(e.get('roadway') or '—'))}</td><td>{escape(str(e.get('description') or ''))[:80]}</td><td>{'Full closure' if e.get('is_full_closure') else (e.get('event_type') or '—')}</td><td>{v(e.get('distance_km'),' km')} {escape(str(e.get('direction') or ''))}</td></tr>" for e in (events or {}).get('events',[])[:10])
 ev_section=f'<section class="panel"><h2>Road events near this location</h2><div style="overflow:auto"><table><tr><th>Roadway</th><th>Description</th><th>Type</th><th>Distance</th></tr>{ev_rows}</table></div></section>' if ev_rows else ''
 map_section=build_map_section(lat,lon,fire,cameras,events,mp)
 valid_label=format_short(fx.get('valid_at'),tz) or '+3h'
 aqhi_outlook_section=f'<section class="panel"><h2>AQHI outlook</h2><div class="aq"><div>Now<b>{v(cap_aqhi(aq.get("aqhi")))}</b></div><div>{escape(valid_label)}<b>{v(cap_aqhi(fx.get("plus_3h")))}</b></div></div></section>'
 blend=aq.get('blend') or {}; pollutant=aq.get('pollutant') or {}; pa=aq.get('purpleair') or {}
 extra=''
 if blend.get('status')=='ok':extra+=f"<div>Blend estimate<b>{v(cap_aqhi(blend.get('value')))}</b><small>confidence {escape(str(blend.get('confidence','—')))}</small></div>"
 if pollutant.get('status')=='ok':extra+=f"<div>PM2.5 (station)<b>{v(pollutant.get('value'),' µg/m³')}</b><small>{escape(str(pollutant.get('station_name','')))} · {v(pollutant.get('distance_km'),' km')}</small></div>"
 if pa.get('status')=='ok':extra+=f"<div>PM2.5 (community)<b>{v(pa.get('pm25'),' µg/m³')}</b><small>{escape(str(pa.get('name','')))} · {v(pa.get('distance_km'),' km')}</small></div>"
 extra_section=f'<section class="panel"><h2>Local air quality readings</h2><div class="aq">{extra}</div></section>' if extra else ''
 tzab=tz_abbrev(tz)
 hourly_rows=''.join(f"<tr><td>{v(format_short(r.get('time'),tz))}</td><td>{v(r.get('temperature_c'),'°C')}</td><td>{v(r.get('precipitation_probability_pct'),'%')}</td><td>{v(r.get('precipitation_mm'),' mm')}</td><td>{v(r.get('wind_gust_kmh'),' km/h')}</td><td>{v(weather_label(r.get('weather_code')))}</td></tr>" for r in w.get('hourly',[])[:12])
 smoke_note=''
 if a['hazards']['air_quality']['risk'] in ('HIGH','EXTREME'):smoke_note='<p style="color:#e8590c"><strong>Note:</strong> the sky-condition column below comes from the weather model and does not detect wildfire smoke or haze — it can read "Clear sky" during a smoke event. Refer to the Overall risk and Air Quality readings above for actual air quality.</p>'
 hourly_section=f'<section class="panel"><h2>Hourly weather outlook <small style="font-weight:normal">(times in {escape(tzab)})</small></h2>{smoke_note}<div style="overflow:auto"><table><tr><th>Time</th><th>Temp</th><th>Precip chance</th><th>Precip</th><th>Gust</th><th>Sky (weather model)</th></tr>{hourly_rows}</table></div></section>' if hourly_rows else ''
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Field Conditions Report</title><link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/><script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script><style>body{{margin:0;background:#0f1720;color:#f4f7fa;font-family:Arial}}header,main,footer{{max-width:1100px;margin:auto;padding:20px}}.panel,.metric,.hazard{{background:#172330;border:1px solid #304152;border-radius:12px;padding:16px}}.grid{{display:grid;gap:12px}}.metrics{{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}}.hazards{{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}}.hazard b,.metric b{{display:block;font-size:25px;margin:8px 0}}.low{{border-color:#2f9e44}}.moderate{{border-color:#e0a800}}.high{{border-color:#e8590c}}.extreme{{border-color:#c92a2a}}.unknown{{border-color:#6c757d}}table{{width:100%;border-collapse:collapse}}td,th{{padding:8px;border-bottom:1px solid #304152;text-align:left}}section{{margin-bottom:15px}}.aq{{display:flex;gap:10px}}.aq div{{flex:1;text-align:center;background:#111c26;padding:14px;border-radius:8px}}.aq b{{display:block;font-size:26px}}.leaflet-container{{background:#111c26}}</style></head><body><header><h1>Field Conditions Report</h1><p>{v(lat)}, {v(lon)} · Generated {escape(format_long(generated_at,tz))}</p><p><a href="/" style="color:#4dabf7">&larr; check a different location</a></p></header><main>{wx_section}{bulletin_section}<section class="panel"><h2>Overall risk: {a['overall_risk']}</h2></section><section class="grid metrics"><div class="metric">Temperature<b>{v(c.get('temperature_c'),'°C')}</b></div><div class="metric">Feels like<b>{v(c.get('apparent_temperature_c'),'°C')}</b></div><div class="metric">Wind<b>{v(c.get('wind_speed_kmh'),' km/h')}</b><small>from {escape(compass(c.get('wind_direction_deg')))}</small></div><div class="metric">Current AQHI<b>{v(cap_aqhi(aq.get('aqhi')))}</b><small>{escape(str(aq.get('station_name','Unavailable')))}</small></div></section><section class="panel"><h2>Hazard assessment</h2><div class="grid hazards">{cards}</div></section><section class="panel"><h2>Summary</h2><ul>{summary_bullets}</ul><h3>Recommendations</h3><ul>{rec}</ul></section>{aqhi_outlook_section}{extra_section}{map_section}{ev_section}{cam_section}{hourly_section}</main><footer>Live on-demand report — not a scheduled/cached page. Confirm official warnings before field work in hazardous conditions.</footer></body></html>'''
