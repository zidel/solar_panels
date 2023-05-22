import argparse
import datetime
import pathlib
import sys

import tqdm

import database
import download_tiles
import util


recheck_interval = datetime.timedelta(days=180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)
    nib_api_key = util.load_key(args.NiB_key)

    new_tiles = tqdm.tqdm(desc='New images')
    now = datetime.datetime.now()
    with db.transaction() as c:
        tiles = database.all_tiles(c)

    positions = set()
    with db.transaction() as c:
        for _, z, x, y in tiles:
            timestamp = database.last_checked(c, z, x, y)
            if timestamp is not None:
                delta = now - timestamp
                if delta < recheck_interval:
                    continue

            positions.add((z, x, y))

    for z, x, y in tqdm.tqdm(positions):
        written, tile_hash = download_tiles.download_single_tile(
                nib_api_key, z, x, y)
        with db.transaction() as c:
            if written:
                database.add_tile(c, z, x, y, tile_hash)
                new_tiles.update()

            database.mark_checked(c, z, x, y)

if __name__ == '__main__':
    sys.exit(main())
