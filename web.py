import random

import flask
import sqlite3

import database
import util


app = flask.Flask(__name__, static_url_path='')


@app.route("/")
def send_index():
    return flask.send_from_directory('web', 'index.html')


@app.route('/static/script.js')
def send_script():
    return flask.send_from_directory('web/static', 'script.js')


@app.route('/api/review/next_tile')
def get_next_tile_for_review():
    db = database.Database('data/tiles.db')
    tiles = db.tiles_for_review(limit=1)
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


@app.route('/api/review/response', methods=['POST'])
def accept_tile_response():
    body = flask.request.json
    tile_hash = body['tile_hash']
    response = body['response']

    if response == 'true':
        has_solar = True
    elif response == 'false':
        has_solar = False
    elif response == 'skip':
        has_solar = None
    else:
        return 400, 'Bad "response" value'

    db = database.Database('data/tiles.db')
    try:
        if has_solar is not None:
            with db.transaction() as c:
                database.set_has_solar(c, tile_hash, has_solar)
        else:
            db.remove_score(tile_hash)
    except sqlite3.IntegrityError as e:
        print(e)

    return {}


@app.route('/api/tiles/by-hash/<tile_hash>.jpeg')
def get_tile_by_hash(tile_hash):
    dir_name = tile_hash[:2]
    file_name = tile_hash[2:]
    return flask.send_from_directory(
            'data/images',
            '{}/{}.jpeg'.format(dir_name, file_name))


@app.route('/api/tiles/by-pos/<z>/<x>/<y>.jpeg')
def get_nib_tile(z, x, y):
    z = int(z)
    x = int(x)
    y = int(y)

    db = database.Database('data/tiles.db')
    with db.transaction() as cursor:
        tiles = database.get_tile_hash(cursor, z, x, y)

    if tiles:
        tile_hash = random.choice(tiles)
    else:
        nib_api_key = util.load_key('secret/NiB_key.json')
        _, tile_hash = util.download_single_tile(
                nib_api_key, z, x, y)
        with db.transaction() as cursor:
            database.add_tile_hash(cursor, z, x, y, tile_hash)

    return flask.redirect(f'/api/tiles/by-hash/{tile_hash}.jpeg', code=302)


if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
