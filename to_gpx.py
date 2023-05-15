import argparse

import database
import util


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='/mnt/NiB/tiles.db')
    args = parser.parse_args()

    db = database.Database(args.database)

    print('<gpx creator="{}" version="1.0">'.format(
        'https://github.com/zidel/solar_panels'))
    for z, x, y in db.tiles_with_solar():
        lat, lon = util.tile2deg(x * 2 + 1, y * 2 + 1, z + 1)
        print('<wpt lat="{}" lon="{}"></wpt>'.format(
            lat,
            lon,
            ))

    print('</gpx>')


if __name__ == '__main__':
    main()
