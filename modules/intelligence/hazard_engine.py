from modules.weather.metrics import humidex,summarize
from core.timefmt import format_short
R={'UNKNOWN':-1,'LOW':0,'MODERATE':1,'HIGH':2,'EXTREME':3}
THRESHOLDS={
 'heat':{'moderate_c':27,'high_c':30,'extreme_c':35},
 'wind_gust_kmh':{'moderate':45,'high':65,'extreme':90},
 'precipitation_probability':{'moderate':40,'high':70},
 'precipitation_mm_hour':{'moderate':2.5,'high':7.5},
 'aqhi':{'moderate':4,'high':7,'extreme':10.01},
 'wind_shear':{'moderate':45,'high':90,'extreme':135},
}
def level(v,m,h,e=None):
    if v is None:return 'UNKNOWN'
    if e is not None and v>=e:return 'EXTREME'
    if v>=h:return 'HIGH'
    if v>=m:return 'MODERATE'
    return 'LOW'
def top(*x):return max(x,key=lambda z:R[z])
def lightning_risk(nearest_km):
    if nearest_km is None:return 'LOW'
    if nearest_km<=10:return 'EXTREME'  # the "30-30 rule" shelter threshold
    if nearest_km<=25:return 'HIGH'
    return 'MODERATE'
def assess(w,aq,fx,tz='America/Edmonton',thresholds=None,shear=None,lightning=None):
    t=thresholds or THRESHOLDS; c=w.get('current',{}); s=summarize(w.get('hourly',[])); hx=humidex(c.get('temperature_c'),c.get('relative_humidity_pct'))
    heatv=max([v for v in (c.get('apparent_temperature_c'),hx,s.get('max_apparent_temperature_c')) if v is not None],default=None); gust=max([v for v in (c.get('wind_gust_kmh'),s.get('max_wind_gust_kmh')) if v is not None],default=None)
    heat=level(heatv,t['heat']['moderate_c'],t['heat']['high_c'],t['heat']['extreme_c']); wind=level(gust,t['wind_gust_kmh']['moderate'],t['wind_gust_kmh']['high'],t['wind_gust_kmh']['extreme'])
    rain=top(level(s.get('max_precipitation_probability_pct'),t['precipitation_probability']['moderate'],t['precipitation_probability']['high']),level(s.get('max_hourly_precipitation_mm'),t['precipitation_mm_hour']['moderate'],t['precipitation_mm_hour']['high']))
    av=max([v for v in (aq.get('aqhi'),(fx or {}).get('plus_3h')) if v is not None],default=None); air=level(av,t['aqhi']['moderate'],t['aqhi']['high'],t['aqhi']['extreme']); thunder='HIGH' if s['thunderstorm_possible'] else ('MODERATE' if (s.get('max_precipitation_probability_pct') or 0)>=60 and (gust or 0)>=45 else 'LOW')
    hazards={'heat':{'risk':heat,'indicator':heatv,'unit':'°C apparent/humidex'},'wind':{'risk':wind,'indicator':gust,'unit':'km/h peak gust'},'precipitation':{'risk':rain,'indicator':s.get('max_hourly_precipitation_mm'),'unit':'mm/h maximum'},'air_quality':{'risk':air,'indicator':av,'unit':'AQHI'},'thunderstorm':{'risk':thunder,'indicator':format_short(s.get('first_thunderstorm_hour'),tz),'unit':'first forecast signal'}}
    # Wind shear: surface vs upper-level HRDPS wind direction divergence (see modules/wind_shear)
    shear=shear or {}; ts=t.get('wind_shear',{'moderate':45,'high':90,'extreme':135})
    hazards['wind_shear']={'risk':level(shear.get('direction_diff_deg'),ts['moderate'],ts['high'],ts['extreme']),'indicator':shear.get('direction_diff_deg'),'unit':f"° direction diff ({shear.get('low_level_m',10)}m vs {shear.get('high_level_m',120)}m)"}
    # Lightning: Environment Canada CLDN proximity (see modules/intelligence/fast_watch) — live at request time, not forecast-inferred
    lightning=lightning or {}
    hazards['lightning']={'risk':lightning_risk(lightning.get('nearest_km')) if lightning.get('status')=='ok' else 'UNKNOWN','indicator':lightning.get('nearest_km'),'unit':'km to nearest strike (CLDN)'}
    return {'overall_risk':top(*[x['risk'] for x in hazards.values()]),'hazards':hazards,'weather_metrics':{'humidex':hx,**s}}
