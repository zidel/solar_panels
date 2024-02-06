import unittest

import util


class UtilTests(unittest.TestCase):
    def testDecodeBuildingGeo(self):
        raw_data = 'POLYGON((4.859207000393244 59.3048083544128,' \
                   '4.856547409705933 59.31364818132525,' \
                   '4.873839298747327 59.31500713151338,' \
                   '4.876494546052094 59.30616682945294,' \
                   '4.859207000393244 59.3048083544128))'
        north, east, south, west = util.decode_geo(raw_data)
        self.assertEqual(59.31500713151338, north)
        self.assertEqual(4.876494546052094, east)
        self.assertEqual(59.3048083544128, south)
        self.assertEqual(4.856547409705933, west)
