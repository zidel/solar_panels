import pathlib
import sqlite3

import flask

import database
import download_tiles
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

    z, x, y, score = list(tiles)[0]

    top, left = util.tile2deg(x, y, z)
    bottom, right = util.tile2deg(x + 1, y + 1, z)

    return {
            'z': z,
            'x': x,
            'y': y,
            'score': score,
            'top': top,
            'left': left,
            'bottom': bottom,
            'right': right,
            }


@app.route('/api/review/response', methods=['POST'])
def accept_tile_response():
    body = flask.request.json
    z = body['z']
    x = body['x']
    y = body['y']
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
                database.set_has_solar(c, z, x, y, has_solar)
        else:
            db.remove_score(z, x, y)
    except sqlite3.IntegrityError as e:
        print(e)

    return {}


@app.route('/api/tiles/<z>/<x>/<y>.jpeg')
def get_nib_tile(z, x, y):
    path = pathlib.Path('data/NiB/{}/{}/{}.jpeg'.format(z, x, y))
    if not path.exists():
        nib_api_key = download_tiles.load_key('secret/NiB_key.json')
        download_tiles.download_single_tile(nib_api_key, z, x, y)

    return flask.send_from_directory(
            'data/NiB',
            '{}/{}/{}.jpeg'.format(z, x, y))


if __name__ == '__main__':
    app.run('0.0.0.0', 5000)
