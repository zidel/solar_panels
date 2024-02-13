import argparse
import pathlib
import os

import sqlite3

import database
import util


def check_variants_of_validation_tiles_not_in_training_set(db):
    print('Checking for tiles that should be in the validation set')

    failure_count = 0
    with db.transaction('fsck_check_train_validate_overlap') as c:
        c.execute('''select count(*)
                     from tile_positions
                     where (z, x, y) not in (
                         select z, x, y
                         from tile_positions
                         natural inner join validation_set
                         )
                  ''')
        failure_count = c.fetchone()[0]

    if failure_count > 0:
        print(f'Found {failure_count} tiles that should be in validation')


def tile_hash_not_in_database(db, tile_path):
    print('Checking for tiles on disk that are not in the database')
    for prefix in os.listdir(tile_path):
        for file_name in os.listdir(tile_path / prefix):
            suffix = file_name.split('.')[0]
            tile_hash = prefix + suffix

            while True:
                try:
                    with db.transaction('fsck_check_for_tile_not_in_db') as c:
                        database.get_tile_pos(c, tile_hash)
                    break
                except sqlite3.OperationalError:
                    pass


def tile_hash_not_on_disk(db, tile_path):
    print('Checking for tiles in the database that are not on disk')
    failure_count = 0
    with db.transaction('fsck_check_for_missing_tile_file') as c:
        for tile_hash in database.all_tile_hashes(c):
            image_path = util.tile_to_paths(tile_path, tile_hash)
            if not image_path.exists():
                failure_count += 1

    if failure_count > 0:
        print(f'Found {failure_count} hashes without a file')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--tile-path', type=str, default='data/images')
    args = parser.parse_args()

    db = database.Database(args.database)

    check_variants_of_validation_tiles_not_in_training_set(db)
    tile_hash_not_in_database(db, pathlib.Path(args.tile_path))
    tile_hash_not_on_disk(db, pathlib.Path(args.tile_path))


if __name__ == '__main__':
    main()
