import hashlib
import json
import math
import time

import requests


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


def nib_url(z, x, y, key):
    fmt = 'https://waapi.webatlas.no/maptiles/tiles' \
            + '/webatlas-orto-newup/wa_grid/{}/{}/{}.jpeg?api_key={}'
    return fmt.format(z, x, y, key)


def download_single_tile(image_dir, nib_api_key, z, x, y):
    start = time.time()

    while True:
        try:
            r = requests.get(nib_url(z, x, y, nib_api_key))
        except requests.exceptions.ConnectionError:
            time.sleep(60)
            continue

        if r.status_code != 200:
            time.sleep(60)
            continue

        break

    h = hashlib.sha256()
    h.update(r.content)
    full_hash = h.hexdigest()
    dir_name = full_hash[:2]
    file_name = full_hash[2:]

    file_path = image_dir / f'{dir_name}/{file_name}.jpeg'
    written = False
    if not file_path.exists():
        file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(file_path, 'wb') as f:
            written = True
            f.write(r.content)

    duration = time.time() - start
    if duration < 0.1:
        time.sleep(0.1 - duration)

    return written, full_hash


def tile_to_paths(tile_dir, tile_hash):
    dir_name = tile_hash[:2]
    file_name = tile_hash[2:]
    return tile_dir / f'{dir_name}/{file_name}.jpeg'
