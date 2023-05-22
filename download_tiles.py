import argparse
import csv
import hashlib
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


def download_single_tile(nib_api_key, z, x, y):
    start = time.time()

    while True:
        r = requests.get(nib_url(z, x, y, nib_api_key))
        if r.status_code != 200:
            time.sleep(60)
            continue

        break

    h = hashlib.sha256()
    h.update(r.content)
    full_hash = h.hexdigest()
    dir_name = full_hash[:2]
    file_name = full_hash[2:]

    # file_path = pathlib.Path(f'/mnt/NiB/images/{dir_name}/{file_name}.jpeg')
    file_path = pathlib.Path(f'data/images/{dir_name}/{file_name}.jpeg')
    written = False
    if not file_path.exists():
        file_path.parent.mkdir(exist_ok=True)
        with open(file_path, 'wb') as f:
            written = True
            f.write(r.content)

    duration = time.time() - start
    if duration < 0.1:
        time.sleep(0.1 - duration)

    return written, full_hash


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
    parser.add_argument('--min-population', default=90000, type=int)
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
                    if database.has_tile(cursor, z, x, y):
                        progress.update()
                        return

                while True:
                    try:
                        written, tile_hash = download_single_tile(
                                nib_api_key, z, x, y)
                        break
                    except Exception as e:
                        progress.display(str(e))
                        time.sleep(60)

                with db.transaction() as cursor:
                    database.add_tile(cursor, z, x, y, tile_hash)

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
