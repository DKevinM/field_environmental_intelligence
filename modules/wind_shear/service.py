"""Surface vs upper-level HRDPS wind direction divergence — same source and
math as edmonton_folk_fest/riders_sitrep's wind_shear module, adapted to
this project's (lat, lon) calling convention for an arbitrary point.

The grid file itself (fetched + gzip-decompressed from Supabase) is ~2.8s
per fetch and only changes on HRDPS's own refresh cycle, so it's cached
the same way modules/fire/service.py caches FIRMS data — fetched once,
reused for every point lookup until stale.
"""
import os,time,gzip,json,requests
from math import atan2,degrees,hypot
from datetime import datetime,timezone
CACHE_TTL_SECONDS=900
_cache={'data':None,'valid_time':None,'forecast_hour':None,'fetched_at':0}
def _num(v):
    try:return float(v)
    except:return None
def _parse(t):return datetime.fromisoformat(t.replace('Z','+00:00'))
def _fetch_grid(timeout):
    now=time.time()
    if _cache['data'] is not None and (now-_cache['fetched_at'])<CACHE_TTL_SECONDS:
        return _cache['data'],_cache['valid_time'],_cache['forecast_hour'],None
    base=os.environ.get('SUPABASE_URL'); key=os.environ.get('SUPABASE_SERVICE_KEY')
    if not base or not key:return None,None,None,{'status':'missing','reason':'SUPABASE_URL/SUPABASE_SERVICE_KEY not set'}
    headers={'apikey':key,'Authorization':f'Bearer {key}'}
    try:
        url=f"{base}/rest/v1/wind_files?select=run_time,forecast_hour,valid_time,file_path&model=eq.HRDPS&order=run_time.desc,forecast_hour.asc&limit=40"
        r=requests.get(url,headers=headers,timeout=timeout); r.raise_for_status(); rows=[x for x in r.json() if x.get('valid_time')]
    except Exception as ex:
        return None,None,None,{'status':'error','error':f'{type(ex).__name__}: {ex}'}
    if not rows:return None,None,None,{'status':'missing','reason':'no HRDPS files recorded'}
    utcnow=datetime.now(timezone.utc)
    row=min(rows,key=lambda x:abs((_parse(x['valid_time'])-utcnow).total_seconds()))
    try:
        obj=requests.get(f"{base}/storage/v1/object/public/winds/{row['file_path']}",headers=headers,timeout=timeout)
        obj.raise_for_status(); data=json.loads(gzip.decompress(obj.content))
    except Exception as ex:
        return None,None,None,{'status':'error','error':f'{type(ex).__name__}: {ex}'}
    _cache.update(data=data,valid_time=row['valid_time'],forecast_hour=row.get('forecast_hour'),fetched_at=now)
    return data,row['valid_time'],row.get('forecast_hour'),None
def load_wind_shear(lat,lon,low_m=10,high_m=120,timeout=20):
    data,valid_time,forecast_hour,err=_fetch_grid(timeout)
    if err:return err
    g=data.get('grid') or {}; lo1,la1,dx,dy,nx,ny=g.get('lo1'),g.get('la1'),g.get('dx'),g.get('dy'),g.get('nx'),g.get('ny')
    if None in (lo1,la1,dx,dy,nx,ny):return {'status':'error','error':'grid metadata missing from stored file'}
    col=min(max(round((lon-lo1)/dx),0),nx-1); rowi=min(max(round((la1-lat)/dy),0),ny-1)
    f=data.get('fields') or {}
    def cell(key):
        v=f.get(key)
        try:return v[0][rowi][col] if v is not None else None
        except Exception:return None
    u_lo,v_lo,u_hi,v_hi=cell(f'ugrd{low_m}'),cell(f'vgrd{low_m}'),cell(f'ugrd{high_m}'),cell(f'vgrd{high_m}')
    if None in (u_lo,v_lo,u_hi,v_hi):return {'status':'missing','reason':f'wind components unavailable at {low_m}m/{high_m}m for this grid cell','valid_time':valid_time}
    dir_lo=(degrees(atan2(u_lo,v_lo))+180)%360; dir_hi=(degrees(atan2(u_hi,v_hi))+180)%360
    diff=abs(dir_hi-dir_lo); diff=min(diff,360-diff)
    return {'status':'ok','valid_time':valid_time,'forecast_hour':forecast_hour,'low_level_m':low_m,'high_level_m':high_m,
            'surface_wind_dir_deg':round(dir_lo,1),'surface_wind_speed_kmh':round(hypot(u_lo,v_lo)*3.6,1),
            'upper_wind_dir_deg':round(dir_hi,1),'upper_wind_speed_kmh':round(hypot(u_hi,v_hi)*3.6,1),
            'direction_diff_deg':round(diff,1)}
