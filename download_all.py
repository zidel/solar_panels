import argparse
import pathlib
import sys

import tqdm

import database
import download_tiles
import util


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
        positions = set()
        for _, z, x, y in tiles:
            positions.add((z, x, y))

        for z, x, y in tqdm.tqdm(positions):
            written, tile_hash = download_tiles.download_single_tile(nib_api_key, z, x, y)
            if written:
                database.add_tile(cursor, z, x, y, tile_hash)

if __name__ == '__main__':
    sys.exit(main())
