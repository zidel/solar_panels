import argparse
import datetime
import random

import database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    args = parser.parse_args()

    db = database.Database(args.database)
    now = datetime.datetime.now()
    timestamp = now.isoformat()
    with db.transaction() as c:
        for tile_hash, in database.all_tile_hashes(c):
            database.write_score(c, tile_hash, random.random(),
                                 'random', timestamp)


if __name__ == '__main__':
    main()
