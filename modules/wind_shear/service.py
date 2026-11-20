"""Surface vs upper-level HRDPS wind direction divergence — same source and
math as edmonton_folk_fest/riders_sitrep's wind_shear module, adapted to
this project's (lat, lon) calling convention for an arbitrary point.

The grid file itself (fetched + gzip-decompressed from Supabase) is ~2.8s
per fetch and only changes on HRDPS's own refresh cycle, so it's cached
the same way modules/fire/service.py caches FIRMS data — fetched once,
reused for every point lookup until stale.
"""
import os,re,time,gzip,json,math,requests
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from math import atan2,degrees,hypot
from datetime import datetime,timedelta,timezone
CACHE_TTL_SECONDS=900
_cache={'data':None,'valid_time':None,'forecast_hour':None,'fetched_at':0}
def _num(v):
    try:return float(v)
    except:return None
def _parse(t):return datetime.fromisoformat(t.replace('Z','+00:00'))
# 2026-11-20: read the HRDPS files AB_winds already keeps on this server first. The Supabase path
# below needs SUPABASE_URL/SUPABASE_SERVICE_KEY, which the service's .env never had, so wind
# shear showed UNKNOWN on every live report. Only the 4 wind fields used here are kept in
# memory (the full file is ~0.5 GB parsed, for ~2 s), and a file is re-read only when
# a different model hour becomes the closest one (~every 3 h), not every 15 min.
LOCAL_DIR=os.environ.get('HRDPS_LOCAL_DIR','/opt/airquality/github/AB_winds/met_data')
_NAME=re.compile(r'ab_met_(\d{8})_(\d{2})Z_f(\d{3})\.json\.gz$')
_local={'path':None,'data':None}
def _fetch_local():
    try:names=os.listdir(LOCAL_DIR)
    except OSError:return None
    utcnow=datetime.now(timezone.utc); best=None
    for n in names:
        m=_NAME.match(n)
        if not m:continue
        run=datetime.strptime(m.group(1)+m.group(2),'%Y%m%d%H').replace(tzinfo=timezone.utc); lead=int(m.group(3))
        valid=run+timedelta(hours=lead)
        p=os.path.join(LOCAL_DIR,n)
        if time.time()-os.path.getmtime(p)<120:continue          # ab_met_pull.py may still be writing it
        key=(abs((valid-utcnow).total_seconds()),-run.timestamp())  # closest valid time, then newest run
        if best is None or key<best[0]:best=(key,p,valid,lead)
    if best is None or best[0][0]>6*3600:return None
    _,p,valid,lead=best
    if _local['path']!=p:
        # parse in a throw-away child process so the web service doesn't keep the ~0.5 GB
        try:
            with ProcessPoolExecutor(max_workers=1,mp_context=get_context('spawn')) as ex:
                grid,fields=ex.submit(_extract,p).result(timeout=60)
        except Exception:
            return None
        if grid is None:return None
        _local.update(path=p,data={'grid':grid,'fields':fields},valid=valid.isoformat().replace('+00:00','Z'),lead=lead)
    return _local['data'],_local['valid'],_local['lead'],None
def _extract(path):
    """Child process: the 4 wind fields as float32 arrays (NaN for missing), shaped [1][ny][nx] like the file."""
    import numpy as np
    with gzip.open(path,'rt') as fh:d=json.load(fh)
    if not (d.get('meta') or {}).get('grid_version'):return None,None
    f=d.get('fields') or {}
    out={k:np.array([[np.nan if x is None else x for x in row] for row in f[k][0]],dtype=np.float32)[None] for k in ('ugrd10','vgrd10','ugrd120','vgrd120') if k in f}
    return d.get('grid'),out
def _fetch_grid(timeout):
    loc=_fetch_local()
    if loc is not None:return loc
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
        try:
            x=v[0][rowi][col] if v is not None else None
            return None if x is None or math.isnan(x) else float(x)
        except Exception:return None
    u_lo,v_lo,u_hi,v_hi=cell(f'ugrd{low_m}'),cell(f'vgrd{low_m}'),cell(f'ugrd{high_m}'),cell(f'vgrd{high_m}')
    if None in (u_lo,v_lo,u_hi,v_hi):return {'status':'missing','reason':f'wind components unavailable at {low_m}m/{high_m}m for this grid cell','valid_time':valid_time}
    dir_lo=(degrees(atan2(u_lo,v_lo))+180)%360; dir_hi=(degrees(atan2(u_hi,v_hi))+180)%360
    diff=abs(dir_hi-dir_lo); diff=min(diff,360-diff)
    return {'status':'ok','valid_time':valid_time,'forecast_hour':forecast_hour,'low_level_m':low_m,'high_level_m':high_m,
            'surface_wind_dir_deg':round(dir_lo,1),'surface_wind_speed_kmh':round(hypot(u_lo,v_lo)*3.6,1),
            'upper_wind_dir_deg':round(dir_hi,1),'upper_wind_speed_kmh':round(hypot(u_hi,v_hi)*3.6,1),
            'direction_diff_deg':round(diff,1)}
