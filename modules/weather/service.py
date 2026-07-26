from .open_meteo import fetch
def load_weather(lat,lon,timezone='America/Edmonton',hours=12,timeout=15):
    try:
        return fetch(lat,lon,timezone,hours,timeout)
    except Exception as ex:
        return {'status':'error','error':f'{type(ex).__name__}: {ex}'}
