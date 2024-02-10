import hashlib
import json
import logging
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


def decode_geo(raw_geo):
    if raw_geo.startswith('POLYGON'):
        corners = raw_geo.split('(')[2].split(')')[0].split(',')
    elif raw_geo.startswith('MULTIPOLYGON'):
        corners = raw_geo.split('(')[3].split(')')[0].split(',')

    corners = [corner.split(' ') for corner in corners]

    return {
            'east': float(max([corner[0] for corner in corners])),
            'north': float(max([corner[1] for corner in corners])),
            'west': float(min([corner[0] for corner in corners])),
            'south': float(min([corner[1] for corner in corners])),
            }


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


def download_single_tile(image_dir, nib_api_key, z, x, y, retry=True):
    log = logging.getLogger('download')
    while True:
        try:
            r = requests.get(nib_url(z, x, y, nib_api_key))
        except requests.exceptions.ConnectionError:
            if not retry:
                log.debug('ConnectionError when downloading tile, won\'t retry')
                raise

            log.debug('ConnectionError when downloading tile, retrying in 60s')
            time.sleep(60)
            continue

        if not r.ok:
            if not retry:
                log.debug(f'Reply was status code {r.status_code}, won\'t retry')
                r.raise_for_status()

            log.debug(f'Reply was status code {r.status_code}, retrying in 60s')
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
        log.debug(f'New image at {z}/{x}/{y}, writing to {file_path}')
        file_path.parent.mkdir(exist_ok=True, parents=True)
        with open(file_path, 'wb') as f:
            written = True
            f.write(r.content)
    else:
        log.debug(f'No new image at {z}/{x}/{y}')

    return written, full_hash


def tile_to_paths(tile_dir, tile_hash):
    dir_name = tile_hash[:2]
    file_name = tile_hash[2:]
    return tile_dir / f'{dir_name}/{file_name}.jpeg'
