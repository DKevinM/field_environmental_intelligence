import unittest
from core.geometry import haversine_km,compass
from modules.weather.metrics import humidex
from modules.intelligence.hazard_engine import assess
class Tests(unittest.TestCase):
 def test_distance(self):self.assertAlmostEqual(haversine_km(53.5,-113.5,53.5,-113.5),0,places=5)
 def test_compass(self):self.assertEqual(compass(90),'E')
 def test_humidex(self):self.assertGreater(humidex(30,60),36)
 def test_hazard(self):
  w={'current':{'temperature_c':20,'relative_humidity_pct':50,'apparent_temperature_c':20,'wind_gust_kmh':20},'hourly':[{'time':'x','temperature_c':20,'apparent_temperature_c':20,'precipitation_probability_pct':90,'precipitation_mm':8,'wind_gust_kmh':70,'weather_code':95}]}
  a=assess(w,{'aqhi':3},{'plus_3h':4})
  self.assertEqual(a['hazards']['thunderstorm']['risk'],'HIGH')
 def test_no_winter_thunder_fallback(self):
  w=self._winter(-5,50); w['hourly'][0].update(precipitation_probability_pct=95,wind_gust_kmh=50)
  self.assertEqual(assess(w,{'aqhi':2},{})['hazards']['thunderstorm']['risk'],'LOW')
 def test_wind_chill(self):
  from modules.weather.metrics import wind_chill
  self.assertAlmostEqual(wind_chill(-20,30),-32.6,places=0)   # ECCC chart: -20 C, 30 km/h -> -33
  self.assertIsNone(wind_chill(15,30)); self.assertIsNone(wind_chill(-20,2))
 def _winter(self,t,wind,code=None,snow=0,vis=20000):
  row={'time':'2026-01-10T10:00','temperature_c':t,'apparent_temperature_c':t,'wind_speed_kmh':wind,'wind_gust_kmh':wind,'precipitation_probability_pct':10,'precipitation_mm':0,'snowfall_cm':snow,'visibility_m':vis,'weather_code':code}
  return {'current':{'temperature_c':t,'relative_humidity_pct':70,'apparent_temperature_c':t,'wind_speed_kmh':wind,'wind_gust_kmh':wind},'hourly':[row]}
 def test_cold(self):
  h=assess(self._winter(-30,20),{'aqhi':2},{})['hazards']['cold']
  self.assertEqual(h['risk'],'EXTREME'); self.assertIn('5-10 minutes',h['frostbite'])
  self.assertEqual(assess(self._winter(-18,20),{'aqhi':2},{})['hazards']['cold']['risk'],'HIGH')
  self.assertEqual(assess(self._winter(2,10),{'aqhi':2},{})['hazards']['cold']['risk'],'LOW')
 def test_snow_ice_visibility(self):
  a=assess(self._winter(-1,10,code=66,snow=0,vis=150),{'aqhi':2},{})
  self.assertEqual(a['hazards']['snow_and_ice']['risk'],'HIGH'); self.assertEqual(a['hazards']['visibility']['risk'],'HIGH')
  self.assertEqual(assess(self._winter(-5,10,snow=12),{'aqhi':2},{})['hazards']['snow_and_ice']['risk'],'HIGH')
 def test_eccc_alerts_raise_overall(self):
  wx={'status':'ok','alerts':[{'name':'extreme cold warning','risk_colour':None}]}
  a=assess(self._winter(-5,5),{'aqhi':2},{},wx_alerts=wx)
  self.assertEqual(a['hazards']['eccc_alerts']['risk'],'HIGH'); self.assertEqual(a['overall_risk'],'HIGH')
  wx={'status':'ok','alerts':[{'name':'special weather statement','risk_colour':None}]}
  self.assertEqual(assess(self._winter(-5,5),{'aqhi':2},{},wx_alerts=wx)['hazards']['eccc_alerts']['risk'],'LOW')
  self.assertEqual(assess(self._winter(-5,5),{'aqhi':2},{},wx_alerts={'status':'error'})['hazards']['eccc_alerts']['risk'],'UNKNOWN')
if __name__=='__main__':unittest.main()
