import argparse
import datetime
import json
import pathlib
import requests
import sqlite3

import tqdm

import feature
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


def get_points_from_overpass(feature_name):
    result = run_overpass_query(feature.overpass_query(feature_name))
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
    parser.add_argument('--zoom', type=int, default=18)
    parser.add_argument('--tile-path', type=str, default='data/images')
    parser.add_argument('--feature', type=str, required=True)
    args = parser.parse_args()

    db = database.Database(args.database)
    nib_api_key = util.load_key(args.NiB_key)
    image_dir = pathlib.Path(args.tile_path)

    for point in tqdm.tqdm(get_points_from_overpass(args.feature)):
        xtile, ytile = util.deg2tile(point['lat'], point['lon'], args.zoom)

        have_tiles = False
        with db.transaction() as c:
            if database.get_tile_hash(c, args.zoom, xtile, ytile):
                have_tiles = True

        if not have_tiles:
            _, tile_hash = util.download_single_tile(
                    image_dir, nib_api_key, args.zoom, xtile, ytile)
            with db.transaction() as c:
                database.add_tile_hash(c, args.zoom, xtile, ytile, tile_hash)

        while True:
            try:
                with db.transaction() as c:
                    now = datetime.datetime.now()
                    timestamp = now.isoformat()
                    for tile_hash in database.get_tile_hash(c, args.zoom, xtile, ytile):
                        database.write_score(c, tile_hash, args.feature, 1.0,
                                             'OSM', timestamp)
            except sqlite3.OperationalError as e:
                print(e)
                continue
            break


if __name__ == '__main__':
    main()
