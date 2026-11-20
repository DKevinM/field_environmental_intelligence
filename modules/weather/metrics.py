from math import exp,log
THUNDER={95,96,99}
FREEZING={56,57,66,67}   # freezing drizzle / freezing rain (WMO)
def wind_chill(t,v):
    """ECCC wind chill index (air temp C, 10 m wind km/h); None when it doesn't apply (T > 10 C or wind < 5 km/h)."""
    if t is None or v is None or t>10 or v<5:return None
    return round(13.12+0.6215*t-11.37*v**0.16+0.3965*t*v**0.16,1)
def humidex(t,rh):
    if t is None or rh is None:return None
    a,b=17.625,243.04; g=a*t/(b+t)+log(max(rh,1)/100); d=b*g/(a-g); e=6.11*exp(5417.753*(1/273.16-1/(273.15+d))); return round(t+.5555*(e-10),1)
def summarize(rows):
    def vs(k):return [r[k] for r in rows if r.get(k) is not None]
    def mx(k):
        x=vs(k); return max(x) if x else None
    def mx_time(k):
        pairs=[(r[k],r['time']) for r in rows if r.get(k) is not None]
        return max(pairs,key=lambda p:p[0])[1] if pairs else None
    ts=[r['time'] for r in rows if r.get('weather_code') in THUNDER]
    fz=[r['time'] for r in rows if r.get('weather_code') in FREEZING]
    wc=[(min(x for x in (r.get('temperature_c'),wind_chill(r.get('temperature_c'),r.get('wind_speed_kmh'))) if x is not None),r['time']) for r in rows if r.get('temperature_c') is not None]
    vis=[(r['visibility_m'],r['time']) for r in rows if r.get('visibility_m') is not None]
    snow=vs('snowfall_cm')
    rain=vs('precipitation_mm')
    return {'max_temperature_c':mx('temperature_c'),'max_apparent_temperature_c':mx('apparent_temperature_c'),'max_precipitation_probability_pct':mx('precipitation_probability_pct'),'max_hourly_precipitation_mm':mx('precipitation_mm'),'max_hourly_precipitation_time':mx_time('precipitation_mm'),'total_precipitation_mm':round(sum(rain),1) if rain else None,'max_wind_gust_kmh':mx('wind_gust_kmh'),'thunderstorm_possible':bool(ts),'first_thunderstorm_hour':ts[0] if ts else None,'min_temperature_c':min(vs('temperature_c'),default=None),'min_wind_chill_c':min(wc)[0] if wc else None,'min_wind_chill_time':min(wc)[1] if wc else None,'total_snowfall_cm':round(sum(snow),1) if snow else None,'max_hourly_snowfall_cm':max(snow) if snow else None,'freezing_precip_possible':bool(fz),'first_freezing_precip_hour':fz[0] if fz else None,'min_visibility_m':min(vis)[0] if vis else None,'min_visibility_time':min(vis)[1] if vis else None}
