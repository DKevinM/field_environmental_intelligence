from modules.weather.metrics import humidex,summarize,wind_chill
from core.timefmt import format_short,localize
R={'UNKNOWN':-1,'LOW':0,'MODERATE':1,'HIGH':2,'EXTREME':3}
THRESHOLDS={
 'heat':{'moderate_c':27,'high_c':30,'extreme_c':35},
 'wind_gust_kmh':{'moderate':45,'high':65,'extreme':90},
 'precipitation_probability':{'moderate':40,'high':70},
 'precipitation_mm_hour':{'moderate':2.5,'high':7.5},
 'aqhi':{'moderate':4,'high':7,'extreme':10.01},
 'wind_shear':{'moderate':45,'high':90,'extreme':135},
 # ECCC wind chill risk bands: -10 to -27 moderate; -28 to -39 high (frostbite in 10-30 min);
 # -40 and colder: frostbite in under 10 min, and the Alberta Extreme Cold Warning level.
 'cold_wind_chill':{'moderate':-10,'high':-28,'extreme':-40},
 # snowfall over the next 12 h (cm); ECCC's Alberta snowfall warning is ~10 cm in 12 h
 'snow_cm_12h':{'moderate':2,'high':10,'extreme':25},
 # lowest forecast visibility (m): fog, blowing snow, heavy snow
 'visibility_m':{'moderate':1000,'high':200},
}
# frostbite guidance for exposed skin, from ECCC's wind chill chart
def frostbite_note(wc):
    if wc is None or wc>-28:return None
    if wc<=-55:return 'exposed skin can freeze in under 2 minutes'
    if wc<=-48:return 'exposed skin can freeze in 2-5 minutes'
    if wc<=-40:return 'exposed skin can freeze in 5-10 minutes'
    return 'exposed skin can freeze in 10-30 minutes'
def eccc_alert_risk(wx_alerts):
    """ECCC colour: yellow MODERATE, orange HIGH, red EXTREME. No colour: warning HIGH, watch/advisory MODERATE, statement LOW."""
    if not wx_alerts or wx_alerts.get('status')!='ok':return 'UNKNOWN'
    out='LOW'
    for x in wx_alerts.get('alerts') or []:
        col=(x.get('risk_colour') or '').lower(); name=(x.get('name') or '').lower()
        r={'red':'EXTREME','orange':'HIGH','yellow':'MODERATE'}.get(col)
        if r is None:r='HIGH' if 'warning' in name else ('MODERATE' if ('watch' in name or 'advisory' in name) else 'LOW')
        out=top(out,r)
    return out
def rev_level(v,m,h,e=None):
    """level() for hazards where LOWER is worse (cold, visibility)."""
    if v is None:return 'UNKNOWN'
    return level(-v,-m,-h,None if e is None else -e)
def level(v,m,h,e=None):
    if v is None:return 'UNKNOWN'
    if e is not None and v>=e:return 'EXTREME'
    if v>=h:return 'HIGH'
    if v>=m:return 'MODERATE'
    return 'LOW'
def top(*x):return max(x,key=lambda z:R[z])
def _hours_until(when,observed_at,tz):
    if not when or not observed_at:return None
    now_dt=localize(observed_at,tz); when_dt=localize(when,tz)
    if not now_dt or not when_dt:return None
    return max(0,round((when_dt-now_dt).total_seconds()/3600))
def lightning_risk(nearest_km):
    if nearest_km is None:return 'LOW'
    if nearest_km<=10:return 'EXTREME'  # the "30-30 rule" shelter threshold
    if nearest_km<=25:return 'HIGH'
    return 'MODERATE'
def assess(w,aq,fx,tz='America/Edmonton',thresholds=None,shear=None,lightning=None,wx_alerts=None):
    t=thresholds or THRESHOLDS; c=w.get('current',{}); s=summarize(w.get('hourly',[])); hx=humidex(c.get('temperature_c'),c.get('relative_humidity_pct'))
    heatv=max([v for v in (c.get('apparent_temperature_c'),hx,s.get('max_apparent_temperature_c')) if v is not None],default=None); gust=max([v for v in (c.get('wind_gust_kmh'),s.get('max_wind_gust_kmh')) if v is not None],default=None)
    heat=level(heatv,t['heat']['moderate_c'],t['heat']['high_c'],t['heat']['extreme_c']); wind=level(gust,t['wind_gust_kmh']['moderate'],t['wind_gust_kmh']['high'],t['wind_gust_kmh']['extreme'])
    rain=top(level(s.get('max_precipitation_probability_pct'),t['precipitation_probability']['moderate'],t['precipitation_probability']['high']),level(s.get('max_hourly_precipitation_mm'),t['precipitation_mm_hour']['moderate'],t['precipitation_mm_hour']['high']))
    av=max([v for v in (aq.get('aqhi'),(fx or {}).get('plus_3h')) if v is not None],default=None); air=level(av,t['aqhi']['moderate'],t['aqhi']['high'],t['aqhi']['extreme']); thunder='HIGH' if s['thunderstorm_possible'] else ('MODERATE' if (s.get('max_precipitation_probability_pct') or 0)>=60 and (gust or 0)>=45 and (s.get('max_temperature_c') if s.get('max_temperature_c') is not None else 99)>0 else 'LOW')  # the wet+gusty fallback only above freezing: in winter that's a snow squall, not a thunderstorm
    hazards={'heat':{'risk':heat,'indicator':heatv,'unit':'°C apparent/humidex'},'wind':{'risk':wind,'indicator':gust,'unit':'km/h peak gust'},'precipitation':{'risk':rain,'indicator':s.get('max_hourly_precipitation_mm'),'unit':'mm/h maximum','probability_pct':s.get('max_precipitation_probability_pct'),'peak_in_hours':_hours_until(s.get('max_hourly_precipitation_time'),w.get('observed_at'),tz)},'air_quality':{'risk':air,'indicator':av,'unit':'AQHI'},'thunderstorm':{'risk':thunder,'indicator':format_short(s.get('first_thunderstorm_hour'),tz),'unit':'first forecast signal'}}
    # Wind shear: surface vs upper-level HRDPS wind direction divergence (see modules/wind_shear)
    shear=shear or {}; ts=t.get('wind_shear',{'moderate':45,'high':90,'extreme':135})
    hazards['wind_shear']={'risk':level(shear.get('direction_diff_deg'),ts['moderate'],ts['high'],ts['extreme']),'indicator':shear.get('direction_diff_deg'),'unit':f"° direction diff ({shear.get('low_level_m',10)}m vs {shear.get('high_level_m',120)}m)"}
    # Lightning: ECCC CLDN proximity (see modules/intelligence/fast_watch) — live at request time, not forecast-inferred
    lightning=lightning or {}
    hazards['lightning']={'risk':lightning_risk(lightning.get('nearest_km')) if lightning.get('status')=='ok' else 'UNKNOWN','indicator':lightning.get('nearest_km'),'unit':'km to nearest strike (CLDN)'}
    # Cold: lowest of air temperature and ECCC wind chill, now and over the forecast hours
    tc=t.get('cold_wind_chill',THRESHOLDS['cold_wind_chill'])
    wc_now=wind_chill(c.get('temperature_c'),c.get('wind_speed_kmh'))
    coldv=min([x for x in (c.get('temperature_c'),wc_now,s.get('min_wind_chill_c')) if x is not None],default=None)
    hazards['cold']={'risk':rev_level(coldv,tc['moderate'],tc['high'],tc['extreme']),'indicator':coldv,'unit':'°C coldest wind chill','frostbite':frostbite_note(coldv),'now':wc_now if wc_now is not None else c.get('temperature_c')}
    # Snow and ice: snowfall total + any freezing rain/drizzle in the forecast
    tn=t.get('snow_cm_12h',THRESHOLDS['snow_cm_12h'])
    snow=level(s.get('total_snowfall_cm'),tn['moderate'],tn['high'],tn['extreme'])
    if snow=='UNKNOWN' and s.get('total_snowfall_cm') is None and w.get('hourly'):snow='LOW'
    if s.get('freezing_precip_possible'):snow=top(snow,'HIGH')
    hazards['snow_and_ice']={'risk':snow,'indicator':s.get('total_snowfall_cm'),'unit':'cm snow, next 12 h','freezing_precip':s.get('freezing_precip_possible'),'freezing_from':format_short(s.get('first_freezing_precip_hour'),tz)}
    # Visibility: fog, blowing snow
    tv=t.get('visibility_m',THRESHOLDS['visibility_m'])
    hazards['visibility']={'risk':rev_level(s.get('min_visibility_m'),tv['moderate'],tv['high']),'indicator':s.get('min_visibility_m'),'unit':'m lowest forecast visibility','at':format_short(s.get('min_visibility_time'),tz)}
    # ECCC alerts for this exact spot now count toward the overall rating (winter storm, extreme cold, snowfall, ...)
    hazards['eccc_alerts']={'risk':eccc_alert_risk(wx_alerts),'indicator':len((wx_alerts or {}).get('alerts') or []) if (wx_alerts or {}).get('status')=='ok' else None,'unit':'active for this spot','names':sorted({x.get('name') for x in (wx_alerts or {}).get('alerts') or [] if x.get('name')})}
    return {'overall_risk':top(*[x['risk'] for x in hazards.values()]),'hazards':hazards,'weather_metrics':{'humidex':hx,**s}}
