import os,csv,io,time,requests
from core.geometry import haversine_km,bearing_deg,compass
CONF_MAP={'l':0.3,'n':0.6,'h':0.9}
FIRMS_BASE='https://firms.modaps.eosdis.nasa.gov'
FIRMS_SOURCE='VIIRS_SNPP_NRT'
# Covers all of Alberta plus enough margin that a 150km search radius from any
# point in the province stays inside this box - fetched once and cached rather
# than per-click, since NASA's API can take 5-15s+ to respond.
BROAD_BBOX=(-122.5,47.5,-107.5,62.0)
CACHE_TTL_SECONDS=900
STALE_MAX_SECONDS=7200
_cache={'rows':None,'fetched_at':0}
def num(v):
    try:return float(v)
    except:return None
def confidence_value(v):
    if v in CONF_MAP:return CONF_MAP[v]
    n=num(v)
    return n/100 if n is not None else None
def bbox_for(lat,lon,radius_km):
    dlat=radius_km/111.0
    from math import cos,radians
    dlon=radius_km/(111.0*max(cos(radians(lat)),0.01))
    return lon-dlon,lat-dlat,lon+dlon,lat+dlat
def _fetch_broad(key,day_range=2,timeout=15):
    w,s,e,n=BROAD_BBOX
    url=f"{FIRMS_BASE}/api/area/csv/{key}/{FIRMS_SOURCE}/{w:.4f},{s:.4f},{e:.4f},{n:.4f}/{day_range}"
    r=requests.get(url,timeout=timeout); r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))
def _get_rows(key,day_range,timeout):
    now=time.time()
    if _cache['rows'] is not None and (now-_cache['fetched_at'])<CACHE_TTL_SECONDS:
        return _cache['rows'],None
    try:
        rows=_fetch_broad(key,day_range,timeout)
        _cache['rows']=rows; _cache['fetched_at']=now
        return rows,None
    except Exception as ex:
        err=f'{type(ex).__name__}: {ex}'
        if _cache['rows'] is not None and (now-_cache['fetched_at'])<STALE_MAX_SECONDS:
            return _cache['rows'],None
        return None,err
def load_hotspots(lat,lon,radius_km=150,cluster_km=10,min_confidence=0.30,day_range=2,timeout=15):
    key=os.environ.get('FIRMS_API_KEY')
    if not key:return {'status':'missing','reason':'FIRMS_API_KEY not set in environment'}
    rows,err=_get_rows(key,day_range,timeout)
    if rows is None:return {'status':'error','error':err}
    cand=[]
    for row in rows:
        rlat,rlon=num(row.get('latitude')),num(row.get('longitude'))
        if rlat is None or rlon is None:continue
        cv=confidence_value(row.get('confidence'))
        if cv is not None and cv<min_confidence:continue
        d=haversine_km(lat,lon,rlat,rlon)
        if d>radius_km:continue
        cand.append({'lat':rlat,'lon':rlon,'distance_km':d,'frp':num(row.get('frp')),'confidence':row.get('confidence'),'acq_date':row.get('acq_date'),'acq_time':row.get('acq_time')})
    cand.sort(key=lambda x:x['distance_km'])
    clustered=[]
    for c in cand:
        if any(haversine_km(c['lat'],c['lon'],k['lat'],k['lon'])<=cluster_km for k in clustered):continue
        b=bearing_deg(lat,lon,c['lat'],c['lon'])
        c['direction']=compass(b); c['bearing_deg']=round(b,1); c['distance_km']=round(c['distance_km'],1)
        clustered.append(c)
    if not clustered:return {'status':'ok','count':0,'hotspots':[],'nearest':None}
    return {'status':'ok','count':len(clustered),'hotspots':clustered[:15],'nearest':clustered[0]}
