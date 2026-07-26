from math import radians,sin,cos,atan2,sqrt,degrees
R=6371.0088
def haversine_km(a,b,c,d):
    p1,p2=radians(a),radians(c); dp=radians(c-a); dl=radians(d-b)
    x=sin(dp/2)**2+cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*R*atan2(sqrt(x),sqrt(1-x))
def bearing_deg(a,b,c,d):
    p1,p2=radians(a),radians(c); dl=radians(d-b)
    return (degrees(atan2(sin(dl)*cos(p2),cos(p1)*sin(p2)-sin(p1)*cos(p2)*cos(dl)))+360)%360
def compass(v):
    if v is None:return 'unknown'
    return ['N','NE','E','SE','S','SW','W','NW'][round(v/45)%8]
