import argparse
import datetime
import json
import requests
import sqlite3

import tqdm

import database
import util


def run_overpass_query(query):
    overpass_url = "https://overpass-api.de/api/interpreter"
    params = {'data': query}
    headers = {'User-Agent': 'zidel'}
    request = requests.get(overpass_url,
                           params=params,
                           headers=headers)
    request.raise_for_status()
    return request.text


def get_points_from_overpass():
    result = run_overpass_query(
    '''[out:json][timeout:25];
       area(id:3602978650)->.searchArea;
       way["power"="generator"]
          ["generator:type"="solar_photovoltaic_panel"]
          (area.searchArea);
       out ids center qt; >; out skel qt;
    ''')
    data = json.loads(result)

    points = []
    for element in data['elements']:
        if 'center' in element:
            # {'type': 'way', 'id': 1023439043, 'center': {'lat': 59.9195945, 'lon': 10.632018}}
            points.append(element['center'])
        elif 'lat' in element and 'lon' in element:
            # {'type': 'node', 'id': 9439577222, 'lat': 59.9362591, 'lon': 10.9199213}
            points.append({'lat': element['lat'], 'lon': element['lon']})
        else:
            raise RuntimeError(str(element))

    return points


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    args = parser.parse_args()

    db = database.Database(args.database)
    nib_api_key = util.load_key(args.NiB_key)

    for point in tqdm.tqdm(get_points_from_overpass()):
        xtile, ytile = util.deg2tile(point['lat'], point['lon'], 18)

        have_tiles = False
        with db.transaction() as c:
            if database.get_tile_hash(c, 18, xtile, ytile):
                have_tiles = True

        if not have_tiles:
            _, tile_hash = util.download_single_tile(
                    nib_api_key, 18, xtile, ytile)
            with db.transaction() as c:
                database.add_tile_hash(c, 18, xtile, ytile, tile_hash)

        with db.transaction() as c:
            now = datetime.datetime.now()
            timestamp = now.isoformat()
            for tile_hash in database.get_tile_hash(c, 18, xtile, ytile):
                database.write_score(c, tile_hash, 1.0, 'OSM', timestamp)


if __name__ == '__main__':
    main()
