from pathlib import Path
import csv,gc,io,json,os,requests
def read_structured_source(source,timeout=20):
    if source.startswith(('http://','https://')):
        r=requests.get(source,timeout=timeout,headers={'User-Agent':'EventEnvironmentalIntelligence/1.0'}); r.raise_for_status(); text=r.text
    else:text=Path(source).read_text(encoding='utf-8')
    return list(csv.DictReader(io.StringIO(text))) if source.lower().split('?')[0].endswith('.csv') else json.loads(text)
_cache={}
def read_structured_source_cached(source,timeout=20):
    if source.startswith(('http://','https://')):return read_structured_source(source,timeout)
    try:mtime=os.path.getmtime(source)
    except OSError:return read_structured_source(source,timeout)
    entry=_cache.get(source)
    if entry and entry[0]==mtime:return entry[1]
    data=read_structured_source(source,timeout)
    _cache[source]=(mtime,data)
    # Cached datasets (e.g. firesmoke, AQHI grid) can be 100k+ features. Without
    # this, the cyclic GC keeps re-scanning that static heap on every request's
    # normal allocations, causing latency that grows request over request.
    gc.freeze()
    return data
def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')
