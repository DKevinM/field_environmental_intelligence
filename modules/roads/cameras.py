import os,requests
from core.geometry import haversine_km,bearing_deg,compass
BASE='https://511.alberta.ca/api/v2/get/cameras'
def load_nearby_cameras(lat,lon,radius_km=15,max_cameras=4,timeout=15):
    key=os.environ.get('AB511_API_KEY')
    if not key:return {'status':'missing','reason':'AB511_API_KEY not set in environment'}
    try:
        r=requests.get(BASE,params={'format':'json','key':key},timeout=timeout); r.raise_for_status()
        rows=r.json()
    except Exception as ex:
        return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for c in rows:
        clat,clon=c.get('Latitude'),c.get('Longitude')
        if clat is None or clon is None:continue
        d=haversine_km(lat,lon,clat,clon)
        if d>radius_km:continue
        views=[v for v in (c.get('Views') or []) if v.get('Status')=='Enabled' and v.get('Url')]
        if not views:continue
        b=bearing_deg(lat,lon,clat,clon)
        cand.append({'name':c.get('Location') or c.get('Roadway') or f"Camera {c.get('Id')}",'lat':clat,'lon':clon,'distance_km':round(d,2),'direction':compass(b),'image_url':views[0]['Url']})
    cand.sort(key=lambda x:x['distance_km'])
    return {'status':'ok','count':len(cand),'cameras':cand[:max_cameras]}
