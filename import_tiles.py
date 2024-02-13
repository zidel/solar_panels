import argparse
import csv
import pathlib
import sys

import tqdm

import database
import util


zoom = 18


def read_data(path, data_class, min_count):
    data = []
    with open(path, 'r') as f:
        reader = csv.reader(f, delimiter=',')

        header = next(reader)
        class_index = header.index(data_class)
        geo_index = header.index('geom_wkt')

        for line in reader:
            count = int(line[class_index])
            if count < min_count:
                continue

            raw_geo = line[geo_index]
            try:
                coords = util.decode_geo(raw_geo)
            except:
                print(f'Failed to decode {raw_geo}')
                raise

            coords['count'] = count
            data.append(coords)

    data.sort(
            key=lambda x: x['count'],
            reverse=True)
    return data


def for_each_tile(piece, func):
    min_x, min_y = util.deg2tile(piece['north'], piece['west'], zoom)
    max_x, max_y = util.deg2tile(piece['south'], piece['east'], zoom)

    for x in range(min_x, max_x + 1):
        for y in range(min_y, max_y + 1):
            func(zoom, x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--min-count', type=int)

    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--population', action='store_true')
    source.add_argument('--buildings', action='store_true')
    source.add_argument('--industrial_buildings', action='store_true')
    source.add_argument('--businesses', action='store_true')

    args = parser.parse_args()

    if args.population:
        data_path = 'population.csv'
        data_class = 'pop_tot'
        min_count = 10000
    elif args.buildings:
        data_path = 'buildings.csv'
        data_class = 'bui0all'
        min_count = 5000
    elif args.industrial_buildings:
        data_path = 'buildings.csv'
        data_class = 'bui1ind'
        min_count = 400
    elif args.businesses:
        data_path = 'businesses.csv'
        data_class = 'est_tot'
        min_count = 500
    else:
        raise AssertionError

    if args.min_count:
        min_count = args.min_count

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)

    data = read_data(data_path, data_class, min_count)
    for piece in tqdm.tqdm(data):
        def per_tile(z, x, y):
            with db.transaction('add_imported_tile') as cursor:
                database.add_tile(cursor, z, x, y)

        for_each_tile(piece, per_tile)


if __name__ == '__main__':
    sys.exit(main())
