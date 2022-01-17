import argparse
import csv
import os
import pathlib

import database
import util


def for_each_tile(west, south, east, north, zoom_levels, func):
    for zoom in zoom_levels:
        min_x, min_y = util.deg2tile(north, west, zoom)
        max_x, max_y = util.deg2tile(south, east, zoom)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                func(zoom, x, y)


def import_dataset(path, zoom_levels, tile_func, min_population=None):
    with open(path, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for row in reader:
            west, south, east, north = row[:4]

            if min_population is not None:
                if int(row[4]) < min_population:
                    continue

            for_each_tile(
                    float(west),
                    float(south),
                    float(east),
                    float(north),
                    zoom_levels,
                    tile_func)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--population', default='population.csv')
    parser.add_argument('--min-population', default=1000)
    parser.add_argument('--zoom', action='append', type=int)
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    os.makedirs(db_path.parent, exist_ok=True)
    db = database.Database(db_path)

    with db.transaction() as cursor:
        import_dataset(
                args.population,
                args.zoom,
                lambda z, x, y: database.add_tile(cursor, z, x, y),
                args.min_population)


if __name__ == '__main__':
    main()
