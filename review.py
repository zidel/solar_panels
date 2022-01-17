import argparse
import sqlite3
import subprocess

import database
import download_tiles
import util


tiles_done = []
tiles_todo = []


def add_surrounding_tiles(z, x, y):
    for d_x in [-1, 0, 1]:
        for d_y in [-1, 0, 1]:
            new_x = x + d_x
            new_y = y + d_y
            if (z, new_x, new_y) not in tiles_done + tiles_todo:
                tiles_todo.append((z, new_x, new_y))


def review_single_tile(nib_api_key, db, z, x, y, score):
    with db.transaction() as cursor:
        database.add_tile(cursor, z, x, y)
    download_tiles.download_single_tile(nib_api_key, z, x, y)

    for dataset in ['NiB']:
        path = 'data/{}/{}/{}/{}.jpeg'.format(
                dataset,
                z,
                x,
                y)
        subprocess.run(
                ['xdg-open', path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                )

    lat, lon = util.tile2deg(x * 2 + 1, y * 2 + 1, z + 1)
    osm_url = 'https://www.openstreetmap.org/?mlat={}&mlon={}'.format(
            lat,
            lon)

    print()
    print('OSM link: {}'.format(osm_url))
    print('Score: {}'.format(score))
    response = input(
            'Are there solar panels in this tile? ({}/{}/{}) [y/n/s] '.format(
                z,
                x,
                y,
                ))
    if response == 'y':
        return True
    elif response == 'n':
        return False
    else:
        return None


def review_tile(nib_api_key, db, z, x, y, around, score=0.0):
    tiles_todo.append((z, x, y))

    skipped = 0
    while tiles_todo:
        z, x, y = tiles_todo[0]
        del tiles_todo[0]
        tiles_done.append((z, x, y))

        has_solar = review_single_tile(nib_api_key, db, z, x, y, score)
        if has_solar is None:
            skipped += 1
            continue

        try:
            with db.transaction() as c:
                database.set_has_solar(c, z, x, y, has_solar)
        except sqlite3.IntegrityError as e:
            print(e)

        if has_solar and around:
            add_surrounding_tiles(z, x, y)

    return skipped


def review_by_score(nib_api_key, db, around):
    skipped = 0
    while True:
        tiles = db.training_candidates(limit=skipped + 1)
        for z, x, y, score in tiles:
            skipped += review_tile(nib_api_key, db, z, x, y, around, score)


def review_position(nib_api_key, db, lat, lon, around):
    x, y = util.deg2tile(lat, lon, 18)
    review_tile(nib_api_key, db, 18, x, y, around)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--lat', type=float)
    parser.add_argument('--lon', type=float)
    parser.add_argument('--tile-x', type=int)
    parser.add_argument('--tile-y', type=int)
    parser.add_argument('--around', action='store_true')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    args = parser.parse_args()

    db = database.Database(args.database)
    nib_api_key = download_tiles.load_key(args.NiB_key)

    if args.lat and args.lon:
        review_position(nib_api_key, db, args.lat, args.lon, args.around)
    elif args.tile_x and args.tile_y:
        review_tile(nib_api_key, db, args.tile_x, args.tile_y, args.around)
    else:
        review_by_score(nib_api_key, db, args.around)


if __name__ == '__main__':
    main()
