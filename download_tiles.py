import argparse
import json
import os
import pathlib
import requests
import sys

import database


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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    args = parser.parse_args()

    db = database.Database(args.database)
    nib_api_key = load_key(args.NiB_key)

    total = len(list(db.tiles()))
    done = 0
    for z, x, y in db.tiles():
        sys.stdout.write('\r{}/{}'.format(done, total))
        sys.stdout.flush()
        done += 1
        download_single_tile(nib_api_key, z, x, y)

    sys.stdout.write('\r{}\r'.format(' ' * 40))
    sys.stdout.flush()


if __name__ == '__main__':
    main()
