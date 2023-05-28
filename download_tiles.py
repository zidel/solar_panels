import argparse
import datetime
import pathlib
import sys

import tqdm

import database
import util


recheck_interval = datetime.timedelta(days=180)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--tile-path', type=str, default='data/images')
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    db = database.Database(db_path)
    nib_api_key = util.load_key(args.NiB_key)
    image_dir = pathlib.Path(args.tile_path)

    new_tiles = tqdm.tqdm(desc='New images')
    now = datetime.datetime.now()
    positions = set()
    with db.transaction() as c:
        for z, x, y in database.all_tiles(c):
            timestamp = database.last_checked(c, z, x, y)
            if timestamp is not None:
                delta = now - timestamp
                if delta < recheck_interval:
                    continue

            positions.add((z, x, y))

    for z, x, y in tqdm.tqdm(positions):
        written, tile_hash = util.download_single_tile(
                image_dir, nib_api_key, z, x, y)
        with db.transaction() as c:
            if written:
                database.add_tile_hash(c, z, x, y, tile_hash)
                new_tiles.update()

            database.mark_checked(c, z, x, y)


if __name__ == '__main__':
    sys.exit(main())
