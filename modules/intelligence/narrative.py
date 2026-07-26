from core.geometry import compass
from core.aqhi import cap_str as faqhi, eccc_messages
def f(v,d=0):return 'unavailable' if v is None else f'{v:.{d}f}'
def sensor_label(source='VIIRS_SNPP_NRT'):
    fam=(source or '').split('_')[0]
    return {'VIIRS':'NASA FIRMS – VIIRS','MODIS':'NASA FIRMS – MODIS'}.get(fam,'NASA FIRMS')
def build(w,aq,fx,a,fire=None,events=None,alerts=None,weatherstation=None,wx_alerts=None):
 c=w.get('current',{}); m=a['weather_metrics']; h=a['hazards']
 parts=[f"At this location, temperature is {f(c.get('temperature_c'),1)}°C and feels near {f(c.get('apparent_temperature_c'),1)}°C. Winds are {f(c.get('wind_speed_kmh'))} km/h from {compass(c.get('wind_direction_deg'))}, gusting near {f(c.get('wind_gust_kmh'))} km/h."]
 wx=(wx_alerts or {}).get('alerts') or []
 if wx:parts.append(f"Environment Canada has {len(wx)} active alert(s) in effect for this exact location: {', '.join(sorted(set(x['name'] for x in wx)))}.")
 parts.append(f"The nearest current AQHI is {faqhi(aq.get('aqhi'))} at {aq.get('station_name','the nearest point')}, {f(aq.get('distance_km'),1)} km away." if aq.get('aqhi') is not None else 'A valid current AQHI was not available for this location.')
 pollutant=(aq.get('pollutant') or {})
 if pollutant.get('status')=='ok':parts.append(f"The nearest air monitoring station ({pollutant.get('station_name')}, {f(pollutant.get('distance_km'),1)} km) reports fine particulate matter (PM2.5) at {f(pollutant.get('value'),1)} µg/m³.")
 pa=(aq.get('purpleair') or {})
 if pa.get('status')=='ok':parts.append(f"A nearby community sensor ('{pa.get('name')}', {f(pa.get('distance_km'),1)} km) reads {f(pa.get('pm25'),1)} µg/m³ PM2.5.")
 wd=c.get('wind_direction_deg')
 if wd is not None:parts.append(f"Winds are moving from the {compass(wd)} toward the {compass((wd+180)%360)}.")
 nearest_fire=(fire or {}).get('nearest')
 if nearest_fire:
  align=''
  if wd is not None:
   diff=abs(nearest_fire['bearing_deg']-wd); upwind=min(diff,360-diff)<=45
   align=' This fire is roughly upwind, so smoke exposure at this location is plausible.' if upwind else ''
  parts.append(f"The nearest active fire detection ({sensor_label()}, last {nearest_fire.get('acq_date','—')}) is {nearest_fire['distance_km']} km {nearest_fire['direction']} of this location.{align}")
 if weatherstation:
  parts.append(f"A nearby 511 weather station ({f(weatherstation.get('distance_km'),1)} km) reports {weatherstation.get('air_temperature_c','—')}°C air temperature and wind at {weatherstation.get('wind_speed_kmh','—')} km/h.")
 closures=[e for e in (events or {}).get('events',[]) if e.get('is_full_closure')]
 other_events=[e for e in (events or {}).get('events',[]) if not e.get('is_full_closure')]
 if closures:
  parts.append(f"{len(closures)} full road closure(s) reported within range, nearest: {closures[0].get('roadway') or 'unnamed roadway'} ({f(closures[0].get('distance_km'),1)} km {closures[0].get('direction','')}) — {closures[0].get('description','')}".strip())
 elif other_events:
  parts.append(f"{len(other_events)} road event(s)/incident(s) reported within range, nearest: {other_events[0].get('roadway') or 'unnamed roadway'} ({f(other_events[0].get('distance_km'),1)} km {other_events[0].get('direction','')}).")
 if alerts and alerts.get('status')=='ok' and alerts.get('count'):
  parts.append(f"{alerts['count']} active province-wide weather alert(s) in effect (not location-filtered) — check details before travel.")
 if fx and fx.get('plus_3h') is not None:parts.append(f"The AQHI forecast for the next few hours is {faqhi(fx.get('plus_3h'))}.")
 if m.get('thunderstorm_possible'):parts.append('Thunderstorm conditions appear in the hourly forecast for this location.')
 elif (m.get('max_precipitation_probability_pct') or 0)>=40:parts.append(f"Precipitation probability reaches approximately {f(m.get('max_precipitation_probability_pct'))}%.")
 key=[k.replace('_',' ') for k,v in h.items() if v['risk'] in ('HIGH','EXTREME')]
 headline=f"Overall conditions at this location are {a['overall_risk']}."+(f" Primary concerns are {', '.join(key)}." if key else '')
 parts.append(headline); rec=[]
 if h['thunderstorm']['risk'] in ('HIGH','EXTREME'):rec.append('Lightning risk present — confirm shelter/pause procedures before working outdoors.')
 if h['heat']['risk'] in ('HIGH','EXTREME'):rec.append('High heat — increase hydration, take shade breaks, watch for heat-illness symptoms.')
 if h['wind']['risk'] in ('HIGH','EXTREME'):rec.append('High wind — secure loose equipment, use caution with ladders/elevated work.')
 if h['precipitation']['risk'] in ('HIGH','EXTREME'):rec.append('Heavy precipitation possible — plan for wet-weather PPE and footing hazards.')
 if closures:rec.append('Confirm an alternate route — a full closure is reported near this location.')
 if wx:rec.append(f"Active Environment Canada alert(s) for this location — review details before starting work: {', '.join(sorted(set(x['name'] for x in wx)))}.")
 aqmsg=eccc_messages(h['air_quality']['risk'])
 if aqmsg:
  rec.append(f"Environment Canada AQHI guidance — general population: {aqmsg['general']}")
  rec.append(f"Environment Canada AQHI guidance — at-risk populations: {aqmsg['at_risk']}")
 if not rec:rec=['No elevated hazards detected for this location at this time.']
 return {'headline':headline,'summary':' '.join(parts),'recommendations':rec}
