import argparse
import datetime
import pathlib
import random

import flask
import sqlite3

import database
import util


db_path = None
nib_key_path = None
tile_path = None
feature = None


app = flask.Flask(__name__, static_url_path='')


@app.route("/")
def send_index():
    return flask.send_from_directory('web', 'index.html')


@app.route('/static/script.js')
def send_script():
    return flask.send_from_directory('web/static', 'script.js')


@app.route('/api/review/next_tile')
def get_next_tile_for_review():
    db = database.Database(db_path)
    tiles = db.tiles_for_review(feature, limit=1)
    if not tiles:
        return '', 204

    tile_hash, z, x, y, score, model_version = list(tiles)[0]

    top, left = util.tile2deg(x, y, z)
    bottom, right = util.tile2deg(x + 1, y + 1, z)

    return {
            'tile_hash': tile_hash,
            'z': z,
            'x': x,
            'y': y,
            'score': score,
            'model_version': model_version,
            'top': top,
            'left': left,
            'bottom': bottom,
            'right': right,
            }


def score_neighbours(cursor, own_hash):
    now = datetime.datetime.now().isoformat()
    z, own_x, own_y = database.get_tile_pos(cursor, own_hash)
    for neighbour_x in [own_x - 1, own_x, own_x + 1]:
        for neighbour_y in [own_y - 1, own_y, own_y + 1]:
            for neighbour_hash in database.get_tile_hash(cursor,
                                                         z,
                                                         neighbour_x,
                                                         neighbour_y):
                database.write_score(cursor,
                                     neighbour_hash,
                                     feature,
                                     1.0,
                                     'neighbour',
                                     now)


@app.route('/api/review/response', methods=['POST'])
def accept_tile_response():
    body = flask.request.json
    tile_hash = body['tile_hash']
    response = body['response']

    if response == 'true':
        has_feature = True
    elif response == 'false':
        has_feature = False
    elif response == 'skip':
        has_feature = None
    else:
        return 400, 'Bad "response" value'

    db = database.Database(db_path)
    try:
        if has_feature is not None:
            with db.transaction() as c:
                database.set_has_feature(c, tile_hash, feature, has_feature)
        else:
            db.remove_score(feature, tile_hash)
    except sqlite3.IntegrityError as e:
        print(e)

    return {}


@app.route('/api/review/surrounding', methods=['POST'])
def review_surrounding_tiles():
    body = flask.request.json
    tile_hash = body['tile_hash']

    db = database.Database(db_path)
    while True:
        try:
            with db.transaction() as c:
                score_neighbours(c, tile_hash)
            break
        except sqlite3.OperationalError:
            continue

    return {}


@app.route('/api/tiles/by-hash/<tile_hash>.jpeg')
def get_tile_by_hash(tile_hash):
    dir_name = tile_hash[:2]
    file_name = tile_hash[2:]
    return flask.send_from_directory(
            tile_path,
            '{}/{}.jpeg'.format(dir_name, file_name))


@app.route('/api/tiles/by-pos/<z>/<x>/<y>.jpeg')
def get_nib_tile(z, x, y):
    z = int(z)
    x = int(x)
    y = int(y)

    db = database.Database(db_path)
    with db.transaction() as cursor:
        tiles = database.get_tile_hash(cursor, z, x, y)

    if tiles:
        tile_hash = random.choice(tiles)
    else:
        nib_api_key = util.load_key(nib_key_path)
        written, tile_hash = util.download_single_tile(
                tile_path, nib_api_key, z, x, y)
        if written:
            with db.transaction() as cursor:
                database.add_tile_hash(cursor, z, x, y, tile_hash)

    return flask.redirect(f'/api/tiles/by-hash/{tile_hash}.jpeg', code=307)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default='secret/NiB_key.json')
    parser.add_argument('--tile-path', type=str, default='data/images')
    parser.add_argument('--feature', default='solar', type=str)
    args = parser.parse_args()

    db_path = pathlib.Path(args.database)
    nib_key_path = pathlib.Path(args.NiB_key)
    tile_path = pathlib.Path(args.tile_path)
    feature = args.feature

    app.run('0.0.0.0', 5000)
