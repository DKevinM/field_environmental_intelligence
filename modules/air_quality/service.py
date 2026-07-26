from core.geometry import haversine_km,bearing_deg,compass
from core.io import read_structured_source,read_structured_source_cached
AK=('AQHI','aqhi','value','Value','current_aqhi'); LAT=('latitude','lat','Latitude','LAT'); LON=('longitude','lon','lng','Longitude','LON')
STATION=('station_name','name','station','StationName'); TIME=('timestamp','datetime','time','observed_at','ReadingDate')
F3H=('aqhi_3h','AQHI_3H','aqhi_future_3h','forecast_3h','AQHI_forecast_3h','aqhi_forecast_3h')
CURRENT_SOURCE="/opt/airquality/github/AB_datapull/data/output/aqhi_station_forecast_3h.csv"
FORECAST_SOURCE="/opt/airquality/github/AB_datapull/data/output/aqhi_station_forecast_3h.csv"
BLEND_GRID_FILE="/opt/airquality/github/AB_datapull/data/output/AQHI_Alberta_blend.geojson"
FIRESMOKE_FILE="/opt/airquality/github/AB_datapull/data/output/firesmoke_now.geojson"
POLLUTANT_SOURCE="/opt/airquality/github/AB_datapull/data/last6h.csv"
PURPLEAIR_SOURCE="/opt/airquality/github/AB_datapull/data/AB_PM25_map.json"
def first(d,ks):
    for k in ks:
        if d.get(k) not in (None,''):return d[k]
def num(v):
    try:return float(v)
    except:return None
def records(data):
    if isinstance(data,list):return [x for x in data if isinstance(x,dict)]
    if isinstance(data,dict) and data.get('type')=='FeatureCollection':
        out=[]
        for f in data.get('features',[]):
            p=dict(f.get('properties') or {}); g=f.get('geometry') or {}; c=g.get('coordinates') or []
            if g.get('type')=='Point' and len(c)>1:p.setdefault('longitude',c[0]);p.setdefault('latitude',c[1])
            out.append(p)
        return out
    return [data] if isinstance(data,dict) else []
def load_current_aqhi(lat,lon,radius_km=30):
    try:data=read_structured_source(CURRENT_SOURCE)
    except Exception as ex:return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for r in records(data):
        v=num(first(r,AK)); la=num(first(r,LAT)); lo=num(first(r,LON))
        if v and la is not None and lo is not None:
            d=haversine_km(lat,lon,la,lo)
            if d<=radius_km:cand.append((d,r,v,la,lo))
    if not cand:return {'status':'missing','aqhi':None}
    d,r,v,la,lo=min(cand,key=lambda x:x[0]); b=bearing_deg(lat,lon,la,lo)
    return {'status':'ok','aqhi':round(v,1),'station_name':first(r,STATION) or 'Nearest AQHI point','timestamp':first(r,TIME),'distance_km':round(d,2),'direction':compass(b)}
def load_forecast_aqhi(lat,lon,radius_km=30):
    try:data=read_structured_source(FORECAST_SOURCE)
    except Exception as ex:return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for r in records(data):
        la=num(first(r,LAT)); lo=num(first(r,LON))
        if la is None or lo is None:
            cand.append((0.0,r,None)); continue
        d=haversine_km(lat,lon,la,lo)
        if d<=radius_km:cand.append((d,r,d))
    if not cand:return {'status':'missing'}
    d,r,dist=min(cand,key=lambda x:x[0]); plus3=num(first(r,F3H)); plus3=round(plus3,1) if plus3 is not None else None
    return {'status':'ok' if plus3 is not None else 'missing','station_name':first(r,STATION) or 'Nearest forecast point','distance_km':round(dist,2) if dist is not None else None,'valid_at':first(r,('forecast_valid_time_utc','valid_time','forecast_time')),'plus_3h':plus3}
def load_blend_estimate(lat,lon):
    try:data=read_structured_source_cached(BLEND_GRID_FILE)
    except Exception as ex:return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    for f in data.get('features',[]):
        g=f.get('geometry') or {}
        if g.get('type')!='Polygon':continue
        ring=g['coordinates'][0]; lons=[c[0] for c in ring]; lats=[c[1] for c in ring]
        if min(lons)<=lon<=max(lons) and min(lats)<=lat<=max(lats):
            p=f.get('properties') or {}; v=num(p.get('value'))
            return {'status':'ok' if v is not None else 'no_data','value':v,'confidence':p.get('confidence'),'n_points':p.get('n_points')}
    return {'status':'missing'}
def load_nearest_pollutant(lat,lon,radius_km=30,parameter='Fine Particulate Matter'):
    try:rows=read_structured_source(POLLUTANT_SOURCE)
    except Exception as ex:return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    stations={}
    for r in rows:
        if r.get('ParameterName')!=parameter or num(r.get('Value')) is None:continue
        la=num(r.get('Latitude')); lo=num(r.get('Longitude'))
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d>radius_km:continue
        name=r.get('StationName'); cur=stations.get(name)
        if cur is None or (r.get('ReadingDate') or '')>cur['reading_date']:stations[name]={'distance_km':d,'reading_date':r.get('ReadingDate'),'value':r.get('Value')}
    if not stations:return {'status':'missing'}
    name,rec=min(stations.items(),key=lambda kv:kv[1]['distance_km']); v=num(rec['value'])
    return {'status':'ok' if v is not None else 'no_data','station_name':name,'distance_km':round(rec['distance_km'],2),'value':v,'parameter':parameter}
def load_nearest_purpleair(lat,lon,radius_km=25):
    try:rows=read_structured_source(PURPLEAIR_SOURCE)
    except Exception as ex:return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for r in rows:
        if not r.get('use_for_map'):continue
        la,lo=r.get('latitude'),r.get('longitude')
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d<=radius_km:cand.append((d,r))
    if not cand:return {'status':'missing'}
    d,r=min(cand,key=lambda x:x[0]); pm=r.get('pm_corr') if r.get('pm_corr') is not None else r.get('pm2.5_atm')
    return {'status':'ok' if pm is not None else 'no_data','name':r.get('name'),'distance_km':round(d,2),'pm25':round(pm,1) if pm is not None else None}
