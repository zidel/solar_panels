import argparse
import datetime
import enum
import pathlib
import random
import sys
import time

import requests
import sqlite3
import tqdm

import database
import util


recheck_interval = datetime.timedelta(days=30)
minimum_image_duration = 10


@enum.unique
class DownloadResult(enum.Enum):
    NEW_TILE = enum.auto()
    KNOWN_TILE = enum.auto()
    RECENTLY_CHECKED = enum.auto()
    UNKNOWN_POSITION = enum.auto()
    DOWNLOAD_ERROR = enum.auto()
    DATABASE_ERROR = enum.auto()

    def server_contacted(self):
        return self in [
                self.NEW_TILE,
                self.KNOWN_TILE,
                self.DOWNLOAD_ERROR,
                self.DATABASE_ERROR,
                ]


def download_location(db, image_dir, nib_api_key, z, x, y):
    with db.transaction() as c:
        timestamp = database.last_checked(c, z, x, y)
        if timestamp is not None:
            delta = datetime.datetime.now() - timestamp
            if delta < recheck_interval:
                return DownloadResult.RECENTLY_CHECKED
        else:
            # We only want to try to download if we have seen this position
            # before, this is not the place to add new positions
            if not database.get_tile_hash(c, z, x, y):
                return DownloadResult.UNKNOWN_POSITION

    try:
        written, tile_hash = util.download_single_tile(
                image_dir, nib_api_key, z, x, y, retry=False)
    except requests.exceptions.ConnectionError:
        return DownloadResult.DOWNLOAD_ERROR

    try:
        with db.transaction() as c:
            if written:
                database.add_tile_hash(c, z, x, y, tile_hash)

            database.mark_checked(c, z, x, y)
    except sqlite3.OperationalError:
        # Ignore it and try again in the next round of downloads
        return DownloadResult.DATABASE_ERROR

    return DownloadResult.NEW_TILE if written else DownloadResult.KNOWN_TILE


def neighbours(z, x, y):
    for neighbour_x in [x - 1, x, x + 1]:
        for neighbour_y in [y - 1, y, y + 1]:
            if neighbour_x == x and neighbour_y == y:
                continue

            yield (z, neighbour_x, neighbour_y)


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

    with db.transaction() as c:
        positions = database.all_tiles(c)
    random.shuffle(positions)

    new_tiles = tqdm.tqdm(desc='New')
    downloads = tqdm.tqdm(desc='Checks', total=len(positions))

    while positions:
        start = time.time()

        z, x, y = positions.pop()
        download_result = download_location(db, image_dir, nib_api_key, z, x, y)
        downloads.update()

        if download_result == DownloadResult.NEW_TILE:
            new_tiles.update()

            for z_new, x_new, y_new in neighbours(z, x, y):
                position = (z_new, x_new, y_new)
                downloads.total += 1
                positions.append(position)

        if download_result.server_contacted():
            duration = time.time() - start
            if duration < minimum_image_duration:
                time.sleep(minimum_image_duration - duration)


if __name__ == '__main__':
    sys.exit(main())
