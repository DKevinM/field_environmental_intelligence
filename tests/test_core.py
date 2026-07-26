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
if __name__=='__main__':unittest.main()
