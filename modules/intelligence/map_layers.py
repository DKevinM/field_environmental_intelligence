from core.geometry import haversine_km
from core.io import read_structured_source_cached
from modules.air_quality.service import CURRENT_SOURCE,BLEND_GRID_FILE,PURPLEAIR_SOURCE,FIRESMOKE_FILE,num
def in_bbox(ring,lat,lon,half):
    lons=[c[0] for c in ring]; lats=[c[1] for c in ring]
    return max(lons)>=lon-half and min(lons)<=lon+half and max(lats)>=lat-half and min(lats)<=lat+half
def load_firesmoke(lat,lon,half_degree=0.6):
    try:data=read_structured_source_cached(FIRESMOKE_FILE)
    except Exception:return {'type':'FeatureCollection','features':[]}
    out=[]
    for f in data.get('features',[]):
        g=f.get('geometry') or {}
        if g.get('type')!='Polygon':continue
        if in_bbox(g['coordinates'][0],lat,lon,half_degree):
            p=f.get('properties') or {}
            out.append({'type':'Feature','geometry':g,'properties':{'pm25':p.get('pm25'),'timestamp':p.get('timestamp')}})
    return {'type':'FeatureCollection','features':out}
def load_aqhi_grid(lat,lon,half_degree=0.6):
    try:data=read_structured_source_cached(BLEND_GRID_FILE)
    except Exception:return {'type':'FeatureCollection','features':[]}
    out=[]
    for f in data.get('features',[]):
        g=f.get('geometry') or {}
        if g.get('type')!='Polygon':continue
        if in_bbox(g['coordinates'][0],lat,lon,half_degree):
            p=f.get('properties') or {}
            out.append({'type':'Feature','geometry':g,'properties':{'value':p.get('value'),'color':p.get('color'),'confidence':p.get('confidence'),'n_points':p.get('n_points')}})
    return {'type':'FeatureCollection','features':out}
def load_purpleair_points(lat,lon,radius_km=25):
    try:rows=read_structured_source_cached(PURPLEAIR_SOURCE)
    except Exception:return []
    out=[]
    for r in rows:
        if not r.get('use_for_map'):continue
        la,lo=r.get('latitude'),r.get('longitude')
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d>radius_km:continue
        pm=r.get('pm_corr') if r.get('pm_corr') is not None else r.get('pm2.5_atm')
        out.append({'name':r.get('name'),'lat':la,'lon':lo,'pm25':round(pm,1) if pm is not None else None,'distance_km':round(d,2)})
    return out
def load_station_points(lat,lon,radius_km=40):
    try:rows=read_structured_source_cached(CURRENT_SOURCE)
    except Exception:return []
    out=[]
    for r in rows:
        la,lo=num(r.get('Latitude') or r.get('latitude')),num(r.get('Longitude') or r.get('longitude'))
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d>radius_km:continue
        out.append({'name':r.get('StationName') or r.get('station_name'),'lat':la,'lon':lo,'aqhi':num(r.get('AQHI') or r.get('aqhi') or r.get('value')),'aqhi_3h':num(r.get('AQHI_forecast_3h') or r.get('aqhi_3h')),'distance_km':round(d,2)})
    return out
def build(lat,lon):
    return {'firesmoke':load_firesmoke(lat,lon),'aqhi_grid':load_aqhi_grid(lat,lon),'purpleair':load_purpleair_points(lat,lon),'stations':load_station_points(lat,lon)}
