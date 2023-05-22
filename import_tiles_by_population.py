import argparse
import csv
import pathlib
import sys

import database
import util


def read_population_data(path, min_population):
    pop_data = []

    with open(path, 'r') as f:
        reader = csv.reader(f, delimiter=',')
        for west, south, east, north, pop in reader:
            pop = int(pop)
            if pop < min_population:
                continue

            pop_data.append((
                float(west),
                float(south),
                float(east),
                float(north),
                pop,
                ))

    pop_data.sort(
            key=lambda x: x[4],
            reverse=True)
    return pop_data


def for_each_tile(west, south, east, north, zoom_levels, func):
    for zoom in zoom_levels:
        min_x, min_y = util.deg2tile(north, west, zoom)
        max_x, max_y = util.deg2tile(south, east, zoom)

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                func(zoom, x, y)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--population', default='population.csv')
    parser.add_argument('--min-population', default=10000, type=int)
    parser.add_argument('--zoom', action='append', type=int)
    args = parser.parse_args()

    if not args.zoom:
        print('Must specify at least one zoom level')
        return 1

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)

    pop_data = read_population_data(args.population, args.min_population)
    for west, south, east, north, pop in pop_data:
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
