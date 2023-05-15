import argparse
import csv
import os
import pathlib
import requests
import sys
import time

import tqdm

import database
import util


def nib_url(z, x, y, key):
    fmt = 'https://waapi.webatlas.no/maptiles/tiles' \
            + '/webatlas-orto-newup/wa_grid/{}/{}/{}.jpeg?api_key={}'
    return fmt.format(z, x, y, key)


def download_tile(url: str, dest: pathlib.Path):
    if not dest.parent.exists():
        os.makedirs(dest.parent)

    r = requests.get(url)
    r.raise_for_status()
    with open(dest, 'wb') as f:
        f.write(r.content)


def download_single_tile(nib_api_key, z, x, y):
    nib_dest = pathlib.Path('/mnt/NiB/{}/{}/{}.jpeg'.format(z, x, y))
    if not nib_dest.exists():
        start = time.time()

        download_tile(
                nib_url(z, x, y, nib_api_key),
                nib_dest,
                )

        duration = time.time() - start
        if duration < 1.0:
            time.sleep(1.0 - duration)


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
    parser.add_argument('--database', default='/mnt/NiB/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--population', default='population.csv')
    parser.add_argument('--min-population', default=10000, type=int)
    parser.add_argument('--zoom', action='append', type=int)
    args = parser.parse_args()

    if not args.zoom:
        print('Must specify at least one zoom level')
        return 1

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)

    nib_api_key = util.load_key(args.NiB_key)
    pop_data = read_population_data(args.population, args.min_population)

    tiles_total = 0
    for west, south, east, north, pop in pop_data:
        def per_tile(z, x, y):
            nonlocal tiles_total
            tiles_total += 1

        for_each_tile(
                west,
                south,
                east,
                north,
                args.zoom,
                per_tile)

    with tqdm.tqdm(total=tiles_total) as progress:
        for west, south, east, north, pop in pop_data:
            def per_tile(z, x, y):
                progress.set_postfix_str(
                        'pop={}, z={}, x={}, y={}'.format(pop, z, x, y),
                        refresh=False)

                with db.transaction() as cursor:
                    database.add_tile(cursor, z, x, y)

                while True:
                    try:
                        download_single_tile(nib_api_key, z, x, y)
                        break
                    except Exception as e:
                        progress.display(str(e))
                        time.sleep(60)

                progress.update()

            for_each_tile(
                    west,
                    south,
                    east,
                    north,
                    args.zoom,
                    per_tile)


if __name__ == '__main__':
    sys.exit(main())
