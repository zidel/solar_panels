import argparse
import csv
import pathlib
import sys

import tqdm

import database
import util


def read_building_data(path, building_class, min_count):
    building_data = []

    with open(path, 'r') as f:
        reader = csv.reader(f, delimiter=',')

        header = next(reader)
        class_index = header.index(building_class)
        geo_index = header.index('geom_wkt')

        for line in reader:
            count = int(line[class_index])
            if count < min_count:
                continue

            north, east, south, west = util.decode_geo(line[geo_index])
            building_data.append((
                west,
                south,
                east,
                north,
                count,
                ))

    building_data.sort(
            key=lambda x: x[4],
            reverse=True)
    return building_data


def for_each_tile(west, south, east, north, zoom_levels, func):
    for zoom in zoom_levels:
        min_x, min_y = util.deg2tile(north, west, zoom)
        max_x, max_y = util.deg2tile(south, east, zoom)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                func(zoom, x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--buildings', default='buildings.csv')
    parser.add_argument('--class', default='bui1ind', type=str,
                        dest='building_class')
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--min-count', default=6000, type=int)
    parser.add_argument('--zoom', action='append', type=int)
    args = parser.parse_args()

    if not args.zoom:
        print('Must specify at least one zoom level')
        return 1

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)

    building_data = read_building_data(args.buildings, args.building_class, args.min_count)
    for west, south, east, north, count in tqdm.tqdm(building_data):
        def per_tile(z, x, y):
            with db.transaction() as cursor:
                database.add_tile(cursor, z, x, y)

        for_each_tile(
                west,
                south,
                east,
                north,
                args.zoom,
                per_tile)


if __name__ == '__main__':
    sys.exit(main())
