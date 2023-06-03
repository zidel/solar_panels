import argparse
import datetime
import random

import database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--dataset',
                        required=True,
                        choices=['training', 'validation'],
                        )
    args = parser.parse_args()

    db = database.Database(args.database)
    with db.transaction() as c:
        for tile_hash, in database.unassigned_tile_hashes(c):
            database.assign_to_set(c, tile_hash, args.dataset)


if __name__ == '__main__':
    main()
