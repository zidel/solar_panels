import argparse
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)
    nib_api_key = util.load_key(args.NiB_key)

    with db.transaction() as c:
        tiles = database.all_tiles(c)
        for z, x, y in tqdm.tqdm(tiles):
            download_single_tile(nib_api_key, z, x, y)

if __name__ == '__main__':
    sys.exit(main())
