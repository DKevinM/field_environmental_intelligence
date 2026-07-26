import requests
from core.geometry import haversine_km,bearing_deg,compass
BASE='https://511.alberta.ca/api/v2/get'
def load_nearby_events(lat,lon,radius_km=15,timeout=15):
    try:
        r=requests.get(f'{BASE}/event',params={'format':'json'},timeout=timeout); r.raise_for_status()
        rows=r.json()
    except Exception as ex:
        return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for e in rows:
        la,lo=e.get('Latitude'),e.get('Longitude')
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d>radius_km:continue
        b=bearing_deg(lat,lon,la,lo)
        cand.append({'roadway':e.get('RoadwayName'),'lat':la,'lon':lo,'description':e.get('Description'),'event_type':e.get('EventType'),'event_subtype':e.get('EventSubType'),'is_full_closure':e.get('IsFullClosure'),'lanes_affected':e.get('LanesAffected'),'severity':e.get('Severity'),'distance_km':round(d,2),'direction':compass(b),'start_date':e.get('StartDate'),'planned_end_date':e.get('PlannedEndDate')})
    cand.sort(key=lambda x:x['distance_km'])
    return {'status':'ok','count':len(cand),'events':cand[:15]}
def load_nearby_weatherstations(lat,lon,radius_km=40,timeout=15):
    try:
        r=requests.get(f'{BASE}/weatherstations',params={'format':'json'},timeout=timeout); r.raise_for_status()
        rows=r.json()
    except Exception as ex:
        return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    cand=[]
    for s in rows:
        la,lo=s.get('Latitude'),s.get('Longitude')
        if la is None or lo is None:continue
        d=haversine_km(lat,lon,la,lo)
        if d>radius_km:continue
        cand.append({'distance_km':round(d,2),'air_temperature_c':s.get('AirTemperature'),'wind_speed_kmh':s.get('WindSpeed'),'wind_direction_deg':s.get('WindDirection'),'relative_humidity_pct':s.get('RelativeHumidity'),'pavement_temperature_c':s.get('PavementTemperature')})
    if not cand:return {'status':'missing','count':0}
    cand.sort(key=lambda x:x['distance_km'])
    return {'status':'ok','count':len(cand),'nearest':cand[0]}
def load_active_alerts(timeout=15,limit=5):
    try:
        r=requests.get(f'{BASE}/alerts',params={'format':'json'},timeout=timeout); r.raise_for_status()
        rows=r.json()
    except Exception as ex:
        return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
    return {'status':'ok','count':len(rows),'alerts':[{'message':a.get('Message'),'notes':a.get('Notes')} for a in rows[:limit]],'note':'Province-wide bulletins, not filtered by location.'}
