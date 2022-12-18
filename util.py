import hashlib
import json
import math


def deg2tile(lat_deg, lon_deg, zoom):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)


def tile2deg(x, y, z):
    n = 2.0 ** z
    lon_deg = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)


def hash_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(1024 * 1024)
            if len(data) == 0:
                break

            h.update(data)

    return h.hexdigest()


def load_key(path):
    j = json.load(open(path, 'rb'))
    return j['key']
