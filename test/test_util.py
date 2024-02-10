import unittest

import util


class UtilTests(unittest.TestCase):
    def testDecodeBuildingGeo(self):
        raw_data = 'POLYGON((4.859207000393244 59.3048083544128,' \
                   '4.856547409705933 59.31364818132525,' \
                   '4.873839298747327 59.31500713151338,' \
                   '4.876494546052094 59.30616682945294,' \
                   '4.859207000393244 59.3048083544128))'
        coords = util.decode_geo(raw_data)
        self.assertEqual(59.31500713151338, coords['north'])
        self.assertEqual(4.876494546052094, coords['east'])
        self.assertEqual(59.3048083544128, coords['south'])
        self.assertEqual(4.856547409705933, coords['west'])

    def testDecodePopulationMultipolygon(self):
        raw_data = 'MULTIPOLYGON(((7.468741068492247 57.968023542197926,' \
                                  '7.459336543630983 58.01254577928637,' \
                                  '7.543237091522114 58.017516987818,' \
                                  '7.552539360942586 57.97298620923243,' \
                                  '7.468741068492247 57.968023542197926)))'
        coords = util.decode_geo(raw_data)
        self.assertEqual(58.017516987818, coords['north'])
        self.assertEqual(7.552539360942586, coords['east'])
        self.assertEqual(57.968023542197926, coords['south'])
        self.assertEqual(7.459336543630983, coords['west'])

    def testDecodeManuallyCheckedPopulationMultipolygon(self):
        raw_data = 'MULTIPOLYGON(((10.705897373856347 59.917400794730035,' \
                                  '10.700094747967945 59.962171263572486,' \
                                  '10.78939108941624 59.96505522086577,' \
                                  '10.795074088403094 59.920279584558685,' \
                                  '10.705897373856347 59.917400794730035)))'
        coords = util.decode_geo(raw_data)
        self.assertEqual(59.965055220865770, coords['north'])
        self.assertEqual(10.795074088403094, coords['east'])
        self.assertEqual(59.917400794730035, coords['south'])
        self.assertEqual(10.700094747967945, coords['west'])

    def testBboxFromWay(self):
        way = {'nodes': [{'lat': 59.9683487, 'lon': 11.0526654}]}
        util.bbox_from_way(way)


class OverpassTests(unittest.TestCase):
    small_overpass_reply = '''{
  "version": 0.6,
  "generator": "Overpass API 0.7.61.5 4133829e",
  "osm3s": {
    "timestamp_osm_base": "2024-02-10T12:57:58Z",
    "timestamp_areas_base": "2024-02-10T08:48:15Z",
    "copyright": "The data [...] from www.openstreetmap.org. [...]under ODbL."
  },
  "elements": [

{
  "type": "way",
  "id": 1023339168,
  "nodes": [
    9423996022,
    9437216482,
    9437216486,
    9437216483,
    9437216484,
    9437216485,
    9423996022
  ]
},
{
  "type": "node",
  "id": 9423996022,
  "lat": 59.9683487,
  "lon": 11.0526654
},
{
  "type": "node",
  "id": 9437216482,
  "lat": 59.9683733,
  "lon": 11.0527321
},
{
  "type": "node",
  "id": 9437216483,
  "lat": 59.9683378,
  "lon": 11.0528889
},
{
  "type": "node",
  "id": 9437216484,
  "lat": 59.9682768,
  "lon": 11.0529786
},
{
  "type": "node",
  "id": 9437216485,
  "lat": 59.9682272,
  "lon": 11.0528441
},
{
  "type": "node",
  "id": 9437216486,
  "lat": 59.9683128,
  "lon": 11.0528211
}

  ]
}
'''

    def test_extract_ways_from_overpass_data(self):
        ways = util.ways_from_overpass_data(self.small_overpass_reply)
        self.assertEqual(1, len(ways))

        way = ways[0]
        self.assertEqual(1023339168, way['id'])
        self.assertEqual(7, len(way['nodes']))

        first_node = way['nodes'][0]
        self.assertEqual(9423996022, first_node['id'])
        self.assertEqual(59.9683487, first_node['lat'])
        self.assertEqual(11.0526654, first_node['lon'])
