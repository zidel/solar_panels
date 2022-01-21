import argparse
import csv
import json
import os
import pathlib
import requests
import sys

import database
import util


def nib_url(z, x, y, key):
    fmt = 'https://waapi.webatlas.no/maptiles/tiles' \
            + '/webatlas-orto-newup/wa_grid/{}/{}/{}.jpeg?api_key={}'
    return fmt.format(z, x, y, key)


def load_key(path):
    j = json.load(open(path, 'rb'))
    return j['key']


def download_tile(url: str, dest: pathlib.Path):
    if not dest.parent.exists():
        os.makedirs(dest.parent)

    r = requests.get(url)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        f.write(r.content)


def download_single_tile(nib_api_key, z, x, y):
    nib_dest = pathlib.Path('data/NiB/{}/{}/{}.jpeg'.format(z, x, y))
    if not nib_dest.exists():
        download_tile(
                nib_url(z, x, y, nib_api_key),
                nib_dest,
                )


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
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--population', default='population.csv')
    parser.add_argument('--min-population', default=10000)
    parser.add_argument('--zoom', action='append', type=int)
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    os.makedirs(db_path.parent, exist_ok=True)
    db = database.Database(args.database)

    nib_api_key = load_key(args.NiB_key)
    pop_data = read_population_data(args.population, args.min_population)

    done = 0
    try:
        for west, south, east, north, pop in pop_data:
            sys.stdout.write('\r{}/{} (population {})'.format(
                done,
                len(pop_data),
                pop,
                ))
            sys.stdout.flush()
            done += 1

            def per_tile(z, x, y):
                with db.transaction() as cursor:
                    database.add_tile(cursor, z, x, y)
                download_single_tile(nib_api_key, z, x, y)

            for_each_tile(
                    west,
                    south,
                    east,
                    north,
                    args.zoom,
                    per_tile)
    finally:
        sys.stdout.write('\r{}\r'.format(' ' * 40))
        sys.stdout.flush()


if __name__ == '__main__':
    main()
