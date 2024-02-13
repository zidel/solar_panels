import argparse
import datetime
import requests
import sqlite3

import shapely

import feature
import database
import util


zoom_level = 18


def run_overpass_query(query):
    overpass_url = "https://overpass-api.de/api/interpreter"
    params = {'data': query}
    headers = {'User-Agent': 'zidel'}
    request = requests.get(overpass_url,
                           params=params,
                           headers=headers)
    request.raise_for_status()
    return request.text


def intersect_way_with_tile(db, way, tile):
    way_poly = shapely.Polygon([(node['lat'], node['lon'])
                                for node in way['nodes']])

    tile_min_lat, tile_min_lon = util.tile2deg(tile['x'], tile['y'], zoom_level)
    tile_max_lat, tile_max_lon = util.tile2deg(tile['x'] + 1, tile['y'] + 1, zoom_level)
    tile_poly = shapely.Polygon([
        (tile_min_lat, tile_min_lon),
        (tile_min_lat, tile_max_lon),
        (tile_max_lat, tile_max_lon),
        (tile_max_lat, tile_min_lon),
        ])

    intersect = way_poly.intersection(tile_poly)
    return intersect.area * 1e9


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--feature', type=str, required=True)
    args = parser.parse_args()

    now = datetime.datetime.now()
    timestamp = now.isoformat()

    db = database.Database(args.database)
    overpass_query = feature.overpass_query(args.feature)
    overpass_raw_data = run_overpass_query(overpass_query)
    overpass_ways = util.ways_from_overpass_data(overpass_raw_data)

    tile_scores = {}
    for way in overpass_ways:
        bbox = util.bbox_from_way(way)
        min_x, min_y = util.deg2tile(bbox['max_lat'], bbox['min_lon'], zoom_level)
        max_x, max_y = util.deg2tile(bbox['min_lat'], bbox['max_lon'], zoom_level)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                area = intersect_way_with_tile(db, way, {'x': x, 'y': y})
                try:
                    tile_scores[(x, y)] += area
                except KeyError:
                    tile_scores[(x, y)] = area

    with db.transaction('write_area_from_osm') as c:
        for x, y in tile_scores:
            database.add_tile(c, zoom_level, x, y)
            area = tile_scores[(x, y)]

            for tile_hash in database.get_tile_hash(c, zoom_level, x, y):
                database.write_score(c,
                                     tile_hash,
                                     args.feature,
                                     area,
                                     'OSM',
                                     timestamp)


if __name__ == '__main__':
    main()
