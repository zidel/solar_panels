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
